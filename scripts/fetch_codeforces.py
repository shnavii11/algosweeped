"""
Codeforces problem corpus fetcher.

Layer order:
  1. Codeforces official API  (problemset.problems)  ← main
  2. clist.by aggregator API                          ← alternate 1
  3. Open GitHub dataset dumps                        ← alternate 2
  4. Direct HTTP scrape (opt-in, FETCH_CF_STATEMENTS) ← alternate 3

Writes directly to Supabase: questions, question_topics, fetch_runs.
"""
import asyncio
import json
import os
import re
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

CF_API = "https://codeforces.com/api"
FETCH_STATEMENTS = os.getenv("FETCH_CF_STATEMENTS", "false").lower() == "true"

with open(ROOT / "scripts/lib/cf_tag_map.json") as f:
    CF_TAG_MAP: dict = json.load(f)


def map_tags(tags: list[str]) -> list[str]:
    mapped = {CF_TAG_MAP.get(t.lower(), None) for t in tags}
    mapped.discard(None)
    return list(mapped) or ["arrays"]


def rating_to_difficulty(rating: int | None) -> str:
    if rating is None:
        return "medium"
    if rating <= 1200:
        return "easy"
    if rating <= 1900:
        return "medium"
    return "hard"


def build_problem(p: dict, stats_map: dict) -> dict:
    cid = p["contestId"]
    idx = p["index"]
    pid = f"cf-{cid}{idx}"
    return {
        "id": pid,
        "platform": "codeforces",
        "number": f"{cid}{idx}",
        "title": p["name"],
        "slug": None,
        "url": f"https://codeforces.com/problemset/problem/{cid}/{idx}",
        "difficulty": rating_to_difficulty(p.get("rating")),
        "difficulty_rating": p.get("rating"),
        "statement_html": None,
        "statement_text": None,
        "constraints": None,
        "examples": None,
        "hints": None,
        "is_premium": False,
        "acceptance_rate": None,
        "solved_count": stats_map.get(f"{cid}_{idx}", {}).get("solvedCount"),
        "raw": json.dumps(p),
        "topics": map_tags(p.get("tags", [])),
    }


# ─── Layer 1: Official API ────────────────────────────────────────────────────

async def fetch_via_official_api(client: httpx.AsyncClient) -> tuple[list[dict], str]:
    print("[CF] Layer 1: Official API…")
    resp = await client.get(f"{CF_API}/problemset.problems", timeout=30)
    data = resp.json()
    if data.get("status") != "OK":
        raise RuntimeError(f"CF API error: {data.get('comment')}")

    problems = data["result"]["problems"]
    statistics = data["result"]["problemStatistics"]
    stats_map = {f"{s['contestId']}_{s['index']}": s for s in statistics}

    result = []
    for p in problems:
        if "contestId" not in p:
            continue
        result.append(build_problem(p, stats_map))

    print(f"[CF] Official API → {len(result)} problems")
    return result, "official_api"


# ─── Layer 2: clist.by ────────────────────────────────────────────────────────

async def fetch_via_clist(client: httpx.AsyncClient) -> tuple[list[dict], str]:
    print("[CF] Layer 2: clist.by…")
    # Free API — requires sign-up for key; falls back gracefully
    api_key = os.getenv("CLIST_API_KEY", "")
    if not api_key:
        raise RuntimeError("CLIST_API_KEY not set")

    problems = []
    offset = 0
    limit = 1000
    while True:
        resp = await client.get(
            "https://clist.by/api/v4/problem/",
            params={"resource": "codeforces.com", "limit": limit, "offset": offset,
                    "format": "json", "username": api_key},
            timeout=30,
        )
        data = resp.json()
        batch = data.get("objects", [])
        if not batch:
            break
        problems.extend(batch)
        offset += limit
        if offset >= data.get("meta", {}).get("total_count", 0):
            break

    result = []
    for p in problems:
        m = re.search(r"/problem/(\d+)/([A-Z]\d*)", p.get("url", ""))
        if not m:
            continue
        cid, idx = m.group(1), m.group(2)
        pid = f"cf-{cid}{idx}"
        result.append({
            "id": pid,
            "platform": "codeforces",
            "number": f"{cid}{idx}",
            "title": p["name"],
            "slug": None,
            "url": p["url"],
            "difficulty": rating_to_difficulty(p.get("rating")),
            "difficulty_rating": p.get("rating"),
            "statement_html": None, "statement_text": None,
            "constraints": None, "examples": None, "hints": None,
            "is_premium": False, "acceptance_rate": None, "solved_count": None,
            "raw": json.dumps(p),
            "topics": [],
        })

    print(f"[CF] clist.by → {len(result)} problems")
    return result, "clist_by"


# ─── Layer 3: Open GitHub dataset ─────────────────────────────────────────────

async def fetch_via_github_dataset(client: httpx.AsyncClient) -> tuple[list[dict], str]:
    print("[CF] Layer 3: GitHub dataset dump…")
    url = "https://raw.githubusercontent.com/agarwalsahil0210/codeforces-problems/master/problems.json"
    resp = await client.get(url, timeout=30)
    raw = resp.json()

    result = []
    for p in (raw if isinstance(raw, list) else raw.get("problems", [])):
        cid = p.get("contestId") or p.get("contest_id")
        idx = p.get("index")
        if not cid or not idx:
            continue
        pid = f"cf-{cid}{idx}"
        result.append({
            "id": pid,
            "platform": "codeforces",
            "number": f"{cid}{idx}",
            "title": p.get("name") or p.get("title", ""),
            "slug": None,
            "url": f"https://codeforces.com/problemset/problem/{cid}/{idx}",
            "difficulty": rating_to_difficulty(p.get("rating")),
            "difficulty_rating": p.get("rating"),
            "statement_html": None, "statement_text": None,
            "constraints": None, "examples": None, "hints": None,
            "is_premium": False, "acceptance_rate": None,
            "solved_count": p.get("solvedCount"),
            "raw": json.dumps(p),
            "topics": map_tags(p.get("tags", [])),
        })

    print(f"[CF] GitHub dataset → {len(result)} problems")
    return result, "github_dataset"


# ─── Layer 4: Statement scraping (opt-in) ─────────────────────────────────────

async def scrape_statement(client: httpx.AsyncClient, url: str) -> dict:
    try:
        from bs4 import BeautifulSoup
        resp = await client.get(url, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        block = soup.select_one(".problem-statement")
        if not block:
            return {}
        html = str(block)
        text = block.get_text(" ", strip=True)
        return {"statement_html": html, "statement_text": text}
    except Exception:
        return {}


async def enrich_statements(problems: list[dict], client: httpx.AsyncClient):
    print(f"[CF] Scraping statements for {len(problems)} problems (FETCH_CF_STATEMENTS=true)…")
    sem = asyncio.Semaphore(3)

    async def enrich_one(p):
        async with sem:
            extra = await scrape_statement(client, p["url"])
            p.update(extra)
            await asyncio.sleep(1.2)

    await asyncio.gather(*[enrich_one(p) for p in problems])


# ─── Orchestrator ─────────────────────────────────────────────────────────────

async def fetch_codeforces() -> list[dict]:
    problems, layer = [], "none"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; icode-scraper/1.0)"}

    async with httpx.AsyncClient(headers=headers) as client:
        for fetch_fn in [fetch_via_official_api, fetch_via_clist, fetch_via_github_dataset]:
            try:
                problems, layer = await fetch_fn(client)
                if problems:
                    break
            except Exception as e:
                print(f"[CF] Layer failed: {e}")

        if FETCH_STATEMENTS and problems:
            await enrich_statements(problems, client)

    return problems, layer


async def main():
    start = datetime.utcnow()
    print("[CF] Starting Codeforces fetch…")

    problems, layer = await fetch_codeforces()

    if not problems:
        print("[CF] All layers failed — no data written.")
        return

    # Write to Supabase
    async with connection() as conn:
        ok = 0
        for p in problems:
            topics = p.pop("topics", [])
            raw_val = p.pop("raw", None)
            p["raw"] = raw_val
            try:
                await upsert_question(conn, p)
                await upsert_question_topics(conn, p["id"], topics)
                ok += 1
            except Exception as e:
                print(f"[CF] Insert error {p['id']}: {e}")

        await upsert_fetch_run(conn, "codeforces", layer, "ok" if ok else "failed",
                               ok, f"fetched {ok}/{len(problems)}")

    # Save snapshot
    snap_dir = ROOT / "data" / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_path = snap_dir / f"codeforces_{datetime.utcnow().strftime('%Y%m%d')}.json"
    with open(snap_path, "w") as f:
        json.dump(problems, f, indent=2)

    print(f"[CF] Done: {ok}/{len(problems)} written. Layer: {layer}. Snapshot: {snap_path}")


if __name__ == "__main__":
    asyncio.run(main())
