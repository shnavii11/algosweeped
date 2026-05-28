"""
LeetCode problem corpus fetcher.

Layer order:
  1. LeetCode official GraphQL  (bulk list + per-problem detail)  ← main
  2. LeetCode MCP servers        (jinzcdev → doggybee → IanLin)  ← alternate 1
  3. Hosted REST wrappers        (alfa-leetcode-api)              ← alternate 2
  4. Browser automation          (Playwright, last resort)        ← alternate 3

Companies are always enriched via open datasets (enrich_companies.py).
Writes directly to Supabase: questions, question_topics, fetch_runs.
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import asyncpg
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

load_dotenv(ROOT / "backend" / ".env")

from lib.db import connection
from lib.upsert import upsert_question, upsert_question_topics, upsert_fetch_run

LC_GRAPHQL = "https://leetcode.com/graphql"
LC_SESSION = os.getenv("LEETCODE_SESSION", "")
LC_CSRF    = os.getenv("LEETCODE_CSRF_TOKEN", "")
CHECKPOINT = ROOT / "data" / ".lc_checkpoint.json"

with open(ROOT / "scripts/lib/lc_topic_map.json") as f:
    LC_TOPIC_MAP: dict = json.load(f)


def map_topics(tag_slugs: list[str]) -> list[str]:
    mapped = {LC_TOPIC_MAP.get(s, None) for s in tag_slugs}
    mapped.discard(None)
    return list(mapped) or ["arrays"]


def make_headers() -> dict:
    h = {
        "Content-Type": "application/json",
        "Referer": "https://leetcode.com",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Origin": "https://leetcode.com",
    }
    if LC_SESSION:
        h["Cookie"] = f"LEETCODE_SESSION={LC_SESSION}; csrftoken={LC_CSRF}"
        h["x-csrftoken"] = LC_CSRF
    return h


# ─── GraphQL queries ──────────────────────────────────────────────────────────

LIST_QUERY = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {
    total: totalNum
    questions: data {
      questionFrontendId
      title
      titleSlug
      difficulty
      topicTags { slug }
      acRate
      paidOnly
    }
  }
}
"""

DETAIL_QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionId
    questionFrontendId
    title
    titleSlug
    content
    difficulty
    topicTags { slug }
    hints
    exampleTestcases
    metaData
    isPaidOnly
    stats
  }
}
"""


async def gql(client: httpx.AsyncClient, query: str, variables: dict, retries=3) -> dict:
    for attempt in range(retries):
        try:
            resp = await client.post(
                LC_GRAPHQL,
                json={"query": query, "variables": variables},
                timeout=20,
            )
            if resp.status_code == 429:
                wait = 2 ** attempt * 2
                print(f"[LC] Rate limited, waiting {wait}s…")
                await asyncio.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(1.5 * (attempt + 1))
    return {}


# ─── Layer 1: LeetCode REST /api/problems/all  (no auth, returns all problems) ─

DIFF_MAP = {1: "easy", 2: "medium", 3: "hard"}


async def fetch_via_rest_all(client: httpx.AsyncClient) -> tuple[list[dict], str]:
    print("[LC] Layer 1: /api/problems/all (no-auth REST)…")
    resp = await client.get("https://leetcode.com/api/problems/all/", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    pairs = data.get("stat_status_pairs", [])
    print(f"[LC] Got {len(pairs)} problems from /api/problems/all")

    # Load checkpoint so per-problem topic enrichment is resumable
    done: dict = {}
    if CHECKPOINT.exists():
        with open(CHECKPOINT) as f:
            done = json.load(f)
        print(f"[LC] Resuming topic-enrichment checkpoint: {len(done)} already done")

    problems_by_slug: dict[str, dict] = {}
    for pair in pairs:
        stat = pair.get("stat", {})
        fid  = stat.get("frontend_question_id") or stat.get("question_id")
        slug = stat.get("question__title_slug", "")
        if not fid or not slug:
            continue
        diff_level = pair.get("difficulty", {}).get("level", 2)
        if slug in done:
            problems_by_slug[slug] = done[slug]
            continue
        problems_by_slug[slug] = {
            "id": f"lc-{fid}",
            "platform": "leetcode",
            "number": str(fid),
            "title": stat.get("question__title", ""),
            "slug": slug,
            "url": f"https://leetcode.com/problems/{slug}/",
            "difficulty": DIFF_MAP.get(diff_level, "medium"),
            "difficulty_rating": None,
            "statement_html": None,
            "statement_text": None,
            "constraints": None,
            "examples": None,
            "hints": None,
            "is_premium": pair.get("paid_only", False),
            "acceptance_rate": round(stat.get("total_acs", 0) / max(stat.get("total_submitted", 1), 1), 4),
            "solved_count": stat.get("total_acs"),
            "raw": json.dumps(pair),
            "topics": [],
        }

    # Enrich topics via GraphQL (best-effort, resumable)
    new_slugs = [s for s in problems_by_slug if s not in done]
    if new_slugs:
        print(f"[LC] Enriching topics for {len(new_slugs)} new problems via GraphQL…")
        sem = asyncio.Semaphore(5)

        async def enrich_topics(slug: str):
            async with sem:
                try:
                    detail_data = await gql(client, DETAIL_QUERY, {"titleSlug": slug})
                    q = detail_data.get("data", {}).get("question") or {}
                    tags = [t["slug"] for t in (q.get("topicTags") or [])]
                    topics = map_topics(tags)
                    problems_by_slug[slug]["topics"] = topics
                    if q.get("content"):
                        problems_by_slug[slug]["statement_html"] = q["content"]
                    if q.get("hints"):
                        problems_by_slug[slug]["hints"] = q["hints"]
                    done[slug] = problems_by_slug[slug]
                    if len(done) % 100 == 0:
                        with open(CHECKPOINT, "w") as f:
                            json.dump(done, f)
                    await asyncio.sleep(0.05)
                except Exception:
                    done[slug] = problems_by_slug[slug]  # save without topics

        await asyncio.gather(*[enrich_topics(s) for s in new_slugs])
        with open(CHECKPOINT, "w") as f:
            json.dump(done, f)

    problems = list(problems_by_slug.values())
    print(f"[LC] /api/problems/all → {len(problems)} problems")
    return problems, "rest_all"


# ─── Layer 2 (fallback): GitHub-hosted LC JSON corpus ─────────────────────────

async def fetch_via_github_corpus(client: httpx.AsyncClient) -> tuple[list[dict], str]:
    print("[LC] Layer 2: GitHub LC corpus dump…")
    # doocs/leetcode hosts a structured JSON of all problems
    url = "https://raw.githubusercontent.com/doocs/leetcode/main/solution/README_EN.md"
    # Simpler: use a known JSON dump repo
    urls = [
        "https://raw.githubusercontent.com/hzfe/awesome-leetcode/master/docs/.vuepress/leetcode-problems.json",
        "https://raw.githubusercontent.com/Bing0/Bing0.github.io/master/leetcode_problems.json",
    ]
    for u in urls:
        try:
            resp = await client.get(u, timeout=30)
            data = resp.json()
            items = data if isinstance(data, list) else data.get("problems", [])
            problems = []
            for p in items:
                fid = p.get("id") or p.get("questionId") or p.get("frontendId")
                slug = p.get("slug") or p.get("titleSlug") or (p.get("link") or "").rstrip("/").split("/")[-1]
                if not fid or not slug:
                    continue
                topics = map_topics(p.get("tags", []) if isinstance(p.get("tags"), list) else [])
                problems.append({
                    "id": f"lc-{fid}",
                    "platform": "leetcode",
                    "number": str(fid),
                    "title": p.get("title", ""),
                    "slug": slug,
                    "url": f"https://leetcode.com/problems/{slug}/",
                    "difficulty": (p.get("difficulty") or "medium").lower(),
                    "difficulty_rating": None,
                    "statement_html": None, "statement_text": None,
                    "constraints": None, "examples": None, "hints": None,
                    "is_premium": p.get("paidOnly") or p.get("premium", False),
                    "acceptance_rate": None, "solved_count": None,
                    "raw": json.dumps(p),
                    "topics": topics,
                })
            if len(problems) > 100:
                print(f"[LC] GitHub corpus → {len(problems)} problems")
                return problems, "github_corpus"
        except Exception as e:
            print(f"[LC] GitHub corpus URL failed: {e}")
    raise RuntimeError("No GitHub corpus URL worked")


# ─── Layer 2: alfa-leetcode-api (hosted REST wrapper) ─────────────────────────

async def fetch_via_rest_wrapper(client: httpx.AsyncClient) -> tuple[list[dict], str]:
    print("[LC] Layer 2: alfa-leetcode-api REST wrapper (paginated)…")
    base = "https://alfa-leetcode-api.onrender.com"
    problems = []
    skip = 0
    page_size = 500

    while True:
        try:
            resp = await client.get(
                f"{base}/problems",
                params={"limit": page_size, "skip": skip},
                timeout=60,
            )
            data = resp.json()
        except Exception as e:
            print(f"[LC] REST page failed at skip={skip}: {e}")
            break

        # Handle both response shapes
        items = (data.get("problemsetQuestionList") or
                 data.get("data", {}).get("problemsetQuestionList") or [])
        if isinstance(items, dict):
            items = items.get("questions") or items.get("data") or []
        if not items:
            break

        for q in items:
            fid = q.get("questionFrontendId") or q.get("frontendId") or q.get("id", "")
            slug = q.get("titleSlug") or q.get("slug", "")
            if not fid or not slug:
                continue
            topics = map_topics([t.get("slug", t) if isinstance(t, dict) else t
                                  for t in q.get("topicTags", [])])
            problems.append({
                "id": f"lc-{fid}",
                "platform": "leetcode",
                "number": str(fid),
                "title": q.get("title", ""),
                "slug": slug,
                "url": f"https://leetcode.com/problems/{slug}/",
                "difficulty": (q.get("difficulty") or "medium").lower(),
                "difficulty_rating": None,
                "statement_html": None, "statement_text": None,
                "constraints": None, "examples": None, "hints": None,
                "is_premium": q.get("paidOnly", False),
                "acceptance_rate": round(q.get("acRate", 0) / 100, 4) if q.get("acRate") else None,
                "solved_count": None, "raw": json.dumps(q),
                "topics": topics,
            })

        print(f"[LC] REST wrapper: {len(problems)} so far (skip={skip})")
        if len(items) < page_size:
            break
        skip += page_size
        await asyncio.sleep(0.3)

    print(f"[LC] REST wrapper total → {len(problems)} problems")
    return problems, "rest_wrapper"


# ─── Layer 3: Playwright browser automation (premium company chips) ────────────

async def fetch_via_playwright(client: httpx.AsyncClient) -> tuple[list[dict], str]:
    """Last resort — only invoked when previous layers return 0 problems."""
    print("[LC] Layer 3: Playwright automation…")
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise RuntimeError("playwright not installed — run: pip install playwright && playwright install chromium")

    stubs_data = await gql(client, LIST_QUERY, {"skip": 0, "limit": 5000})
    stubs = stubs_data.get("data", {}).get("problemsetQuestionList", {}).get("questions", [])

    problems = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx_opts = {}
        if LC_SESSION:
            ctx_opts["storage_state"] = None  # would load from a saved state file
        page = await browser.new_page()
        if LC_SESSION:
            await page.context.add_cookies([
                {"name": "LEETCODE_SESSION", "value": LC_SESSION, "domain": "leetcode.com", "path": "/"},
                {"name": "csrftoken", "value": LC_CSRF, "domain": "leetcode.com", "path": "/"},
            ])

        sem = asyncio.Semaphore(2)

        async def scrape_one(stub):
            slug = stub["titleSlug"]
            fid  = stub["questionFrontendId"]
            async with sem:
                await page.goto(f"https://leetcode.com/problems/{slug}/", wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)
                content = await page.inner_html(".question-content__JfgR, [data-track-load='description_content']") or ""
                topics = map_topics([t["slug"] for t in stub.get("topicTags", [])])
                problems.append({
                    "id": f"lc-{fid}",
                    "platform": "leetcode",
                    "number": str(fid),
                    "title": stub["title"],
                    "slug": slug,
                    "url": f"https://leetcode.com/problems/{slug}/",
                    "difficulty": stub["difficulty"].lower(),
                    "difficulty_rating": None,
                    "statement_html": content or None,
                    "statement_text": None,
                    "constraints": None, "examples": None, "hints": None,
                    "is_premium": stub.get("paidOnly", False),
                    "acceptance_rate": round(stub.get("acRate", 0) / 100, 4) if stub.get("acRate") else None,
                    "solved_count": None, "raw": json.dumps(stub),
                    "topics": topics,
                })
                await asyncio.sleep(2)

        for stub in stubs[:500]:  # cap at 500 for playwright layer
            await scrape_one(stub)

        await browser.close()

    print(f"[LC] Playwright → {len(problems)} problems")
    return problems, "playwright"


# ─── Orchestrator ─────────────────────────────────────────────────────────────

async def fetch_leetcode() -> tuple[list[dict], str]:
    headers = make_headers()
    async with httpx.AsyncClient(headers=headers) as client:
        for fetch_fn in [fetch_via_rest_all, fetch_via_github_corpus, fetch_via_rest_wrapper, fetch_via_playwright]:
            try:
                problems, layer = await fetch_fn(client)
                if len(problems) > 100:
                    return problems, layer
            except Exception as e:
                print(f"[LC] Layer failed: {e}")
    return [], "none"


async def main():
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    print("[LC] Starting LeetCode fetch…")

    problems, layer = await fetch_leetcode()

    if not problems:
        print("[LC] All layers failed — no data written.")
        return

    async with connection() as conn:
        ok = 0
        for p in problems:
            topics = p.pop("topics", [])
            try:
                await upsert_question(conn, p)
                await upsert_question_topics(conn, p["id"], topics)
                ok += 1
            except Exception as e:
                print(f"[LC] Insert error {p.get('id')}: {e}")

        await upsert_fetch_run(conn, "leetcode", layer, "ok" if ok else "failed",
                               ok, f"fetched {ok}/{len(problems)}")

    snap_dir = ROOT / "data" / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_path = snap_dir / f"leetcode_{datetime.utcnow().strftime('%Y%m%d')}.json"
    with open(snap_path, "w") as f:
        json.dump(problems, f, indent=2)

    print(f"[LC] Done: {ok}/{len(problems)} written. Layer: {layer}. Snapshot: {snap_path}")


if __name__ == "__main__":
    asyncio.run(main())
