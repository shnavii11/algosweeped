"""
Aggregate 15+ external DSA sheets → compute optimal curated mix → write to Supabase.

External sheets loaded:
  Striver A2Z, Striver SDE, Blind 75, Neetcode 150/250/All, Grind 75/169,
  Love Babbar 450, LC Top Interview 150, LC Top 100 Liked, AlgoExpert 160,
  CSES, SeanPrashad Patterns, USACO Guide, A2OJ Ladders

Optimal-mix scoring:
  score = 2*cross_sheet_count + topic_coverage_bonus + difficulty_balance_bonus
        + 0.5*log(1+company_freq) + 0.5*editorial_weight
"""
import asyncio
import json
import math
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.db import connection

SHEETS_DIR = ROOT / "data" / "sheets"
SHEETS_DIR.mkdir(parents=True, exist_ok=True)

# Canonical roadmap order
TOPIC_ORDER = [
    "arrays","strings","hashing","two-pointers","sliding-window","prefix-sum",
    "binary-search","linked-list","stacks-queues","recursion","backtracking",
    "trees","bst","heap","greedy","dynamic-programming","graphs","tries",
    "segment-trees","bit-manipulation","math","string-algorithms",
]

# Per-topic quota
QUOTA = {"easy": 8, "medium": 14, "hard": 6}

# Sheet editorial weights (higher = more trusted)
SHEET_WEIGHTS = {
    "neetcode_150": 1.4, "neetcode_250": 1.3, "blind75": 1.3,
    "grind_169": 1.2, "grind_75": 1.2, "striver_sde": 1.2,
    "lc_top_interview_150": 1.1, "striver_a2z": 1.1,
    "lc_top_100_liked": 1.0, "seanprashad_patterns": 1.0,
    "babbar_450": 0.9, "neetcode_all": 0.9,
    "algoexpert_160": 0.9, "cses": 0.8,
    "usaco_guide": 0.7, "a2oj_ladders": 0.7,
}

# ─── Sheet loaders ────────────────────────────────────────────────────────────
#
# Ground truth (re-verified 2026-05-30): the old GitHub-raw URLs for NeetCode,
# Blind75, Grind, Striver and CSES are all dead (404), which is why only the two
# LC GraphQL study-plans resolved. The live sources below verify 100% slug→corpus
# resolution. Sources with no surviving JSON feed (Striver, Grind, CSES, AlgoExpert,
# USACO, A2OJ, NeetCode-250, Babbar) are intentionally NOT fetched — they stay as
# 0-count rows in sheet_sources rather than forced. See step7.md Part 2.

async def _fetch_json(client: httpx.AsyncClient, url: str, cache_name: str):
    """GET url, cache the raw response to data/sheets/<cache_name>, return parsed JSON."""
    resp = await client.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    (SHEETS_DIR / cache_name).write_text(resp.text)
    return resp.json()


async def load_neetcode_master(client: httpx.AsyncClient) -> list[list[dict]]:
    """neetcode-gh master file (450 problems) → three feeds in one fetch.

    Each problem carries {link, pattern, difficulty, neetcode150: bool, blind75: bool}.
    Emits neetcode_all (all 450), neetcode_150 (flag), blind75 (flag).
    """
    data = await _fetch_json(
        client,
        "https://raw.githubusercontent.com/neetcode-gh/leetcode/main/.problemSiteData.json",
        "neetcode_master.json",
    )
    all_e: list[dict] = []
    nc150: list[dict] = []
    blind: list[dict] = []
    for p in data:
        slug = (p.get("link") or "").strip("/").split("/")[-1]
        if not slug:
            continue
        hint = p.get("pattern", "")
        all_e.append({"sheet_id": "neetcode_all", "slug": slug, "platform": "leetcode",
                      "position": len(all_e) + 1, "topic_hint": hint})
        if p.get("neetcode150"):
            nc150.append({"sheet_id": "neetcode_150", "slug": slug, "platform": "leetcode",
                          "position": len(nc150) + 1, "topic_hint": hint})
        if p.get("blind75"):
            blind.append({"sheet_id": "blind75", "slug": slug, "platform": "leetcode",
                          "position": len(blind) + 1, "topic_hint": hint})
    return [all_e, nc150, blind]


async def load_seanprashad(client: httpx.AsyncClient) -> list[dict]:
    """SeanPrashad leetcode-patterns (~178) — carries the LC `slug` directly."""
    data = await _fetch_json(
        client,
        "https://raw.githubusercontent.com/seanprashad/leetcode-patterns/master/src/data/questions.json",
        "seanprashad.json",
    )
    items = data.get("data", []) if isinstance(data, dict) else data
    out = []
    for i, p in enumerate(items):
        slug = (p.get("slug") or "").strip("/")
        if not slug:
            continue
        pat = p.get("pattern")
        hint = pat[0] if isinstance(pat, list) and pat else (pat or "")
        out.append({"sheet_id": "seanprashad_patterns", "slug": slug, "platform": "leetcode",
                    "position": i + 1, "topic_hint": hint})
    return out


async def load_lc_studyplan(client: httpx.AsyncClient, sheet_id: str, plan_slug: str) -> list[dict]:
    """Load LC official study plans via GraphQL."""
    query = """
    query studyPlanDetail($slug: String!) {
      studyPlanV2Detail(planSlug: $slug) {
        planSubGroups { questions { titleSlug difficulty topicTags { slug } } }
      }
    }
    """
    try:
        resp = await client.post(
            "https://leetcode.com/graphql",
            json={"query": query, "variables": {"slug": plan_slug}},
            headers={"Referer": "https://leetcode.com", "Content-Type": "application/json"},
            timeout=20,
        )
        groups = resp.json().get("data",{}).get("studyPlanV2Detail",{}).get("planSubGroups",[])
        out = []
        pos = 1
        for g in groups:
            for q in g.get("questions", []):
                out.append({"sheet_id": sheet_id, "slug": q.get("titleSlug",""),
                            "platform": "leetcode", "position": pos,
                            "topic_hint": q.get("topicTags",[{}])[0].get("slug","") if q.get("topicTags") else ""})
                pos += 1
        return out
    except Exception:
        return []


async def load_all_sheets(client: httpx.AsyncClient) -> list[list[dict]]:
    """Return a flat list of per-sheet batches from the live sources only.

    NeetCode master yields three batches in one fetch; the rest are single batches.
    """
    batches: list[list[dict]] = []

    # NeetCode master → neetcode_all / neetcode_150 / blind75 (one fetch, three feeds).
    try:
        batches.extend(await load_neetcode_master(client))
    except Exception as e:
        print(f"[sheets] neetcode_master load error: {e!r}")

    singles = [
        ("seanprashad_patterns", load_seanprashad(client)),
        ("lc_top_interview_150", load_lc_studyplan(client, "lc_top_interview_150", "top-interview-150")),
        ("lc_top_100_liked", load_lc_studyplan(client, "lc_top_100_liked", "top-100-liked")),
    ]
    results = await asyncio.gather(*(c for _, c in singles), return_exceptions=True)
    for (name, _), res in zip(singles, results):
        if isinstance(res, Exception):
            print(f"[sheets] {name} load error: {res!r}")
        elif res:
            batches.append(res)

    return batches


# ─── Scoring & selection ──────────────────────────────────────────────────────

def compute_optimal_mix(slug_to_qid: dict, qid_to_meta: dict,
                        slug_appearances: dict[str, list[dict]],
                        company_freq: dict[str, int],
                        fallback_corpus: bool = False) -> list[dict]:
    """
    Returns list of {sheet_id, question_id, topic, ordinal, cross_sheet_count,
                     source_sheets, score} dicts.
    """
    selected = []
    globally_selected: set[str] = set()
    topic_difficulty_count: dict[str, dict[str, int]] = {t: {"easy":0,"medium":0,"hard":0} for t in TOPIC_ORDER}

    for topic in TOPIC_ORDER:
        # Collect candidates for this topic (skip globally already-selected questions)
        candidates = []
        for slug, appearances in slug_appearances.items():
            qid = slug_to_qid.get(slug)
            if not qid or qid in globally_selected:
                continue
            meta = qid_to_meta.get(qid, {})
            if topic not in meta.get("topics", []):
                continue
            diff = meta.get("difficulty", "medium")
            cross = len(appearances)
            source_ids = list({a["sheet_id"] for a in appearances})
            editorial_w = sum(SHEET_WEIGHTS.get(s, 1.0) for s in source_ids)
            cf = company_freq.get(qid, 0)

            # difficulty balance bonus
            quota_used = topic_difficulty_count[topic].get(diff, 0)
            diff_bonus = 1 if quota_used < QUOTA.get(diff, 14) else 0

            # topic coverage bonus
            total_topic = sum(topic_difficulty_count[topic].values())
            cov_bonus = 1 if total_topic < 8 else 0

            score = (2 * cross) + cov_bonus + diff_bonus + \
                    0.5 * math.log(1 + cf) + 0.5 * editorial_w

            candidates.append({
                "question_id": qid,
                "difficulty": diff,
                "cross_sheet_count": cross,
                "source_sheets": source_ids,
                "score": round(score, 4),
            })

        # Sort by score desc, then question_id asc for stability
        candidates.sort(key=lambda x: (-x["score"], x["question_id"]))

        # Greedy pick respecting per-difficulty quotas
        ordinal = 1
        topic_picked = set()
        for c in candidates:
            diff = c["difficulty"]
            if topic_difficulty_count[topic][diff] >= QUOTA.get(diff, 14):
                continue
            if c["question_id"] in topic_picked:
                continue
            topic_difficulty_count[topic][diff] += 1
            topic_picked.add(c["question_id"])
            globally_selected.add(c["question_id"])
            selected.append({
                "sheet_id": "optimal_mix_v1",
                "question_id": c["question_id"],
                "topic": topic,
                "ordinal": ordinal,
                "cross_sheet_count": c["cross_sheet_count"],
                "source_sheets": c["source_sheets"],
                "score": c["score"],
            })
            ordinal += 1
            if ordinal > sum(QUOTA.values()):
                break

        # Fallback: if topic has < 4 problems, pull top problems from corpus directly
        if fallback_corpus and ordinal <= 4:
            corpus_candidates = []
            for qid, meta in qid_to_meta.items():
                if qid in globally_selected:
                    continue
                if topic not in meta.get("topics", []):
                    continue
                diff = meta.get("difficulty", "medium")
                cf = company_freq.get(qid, 0)
                score = 0.5 * math.log(1 + cf) + (1 if diff == "easy" else 0)
                corpus_candidates.append({"question_id": qid, "difficulty": diff, "score": score})
            corpus_candidates.sort(key=lambda x: (-x["score"], x["question_id"]))
            fallback_target = 8
            for c in corpus_candidates[:fallback_target * 6]:
                if ordinal > fallback_target:
                    break
                diff = c["difficulty"]
                if topic_difficulty_count[topic][diff] >= QUOTA.get(diff, 14):
                    continue
                topic_difficulty_count[topic][diff] += 1
                globally_selected.add(c["question_id"])
                selected.append({
                    "sheet_id": "optimal_mix_v1",
                    "question_id": c["question_id"],
                    "topic": topic,
                    "ordinal": ordinal,
                    "cross_sheet_count": 0,
                    "source_sheets": [],
                    "score": c["score"],
                })
                ordinal += 1

    return selected


# ─── Main ────────────────────────────────────────────────────────────────────

async def main():
    print("[sheets] Fetching all external sheets…")
    async with httpx.AsyncClient() as client:
        results = await load_all_sheets(client)

    all_entries: list[dict] = []
    sheet_counts: dict[str, int] = {}
    for batch in results:
        if isinstance(batch, Exception):
            print(f"[sheets] Sheet load error: {batch}")
            continue
        for e in batch:
            if e.get("slug"):
                all_entries.append(e)
        if batch and not isinstance(batch, Exception):
            sid = batch[0]["sheet_id"] if batch else "?"
            sheet_counts[sid] = len(batch)

    print(f"[sheets] Total entries across all sheets: {len(all_entries)}")
    for k, v in sheet_counts.items():
        print(f"  {k}: {v}")

    # Save raw sheet data
    with open(SHEETS_DIR / "all_entries.json", "w") as f:
        json.dump(all_entries, f)

    async with connection() as conn:
        # Build lookup tables from DB
        q_rows = await conn.fetch(
            "SELECT id, slug, difficulty FROM questions WHERE platform='leetcode' AND slug IS NOT NULL"
        )
        slug_to_qid = {r["slug"]: r["id"] for r in q_rows}
        qid_to_meta: dict[str, dict] = {}
        for r in q_rows:
            qid_to_meta[r["id"]] = {"difficulty": r["difficulty"] or "medium", "topics": []}

        # Attach topics
        topic_rows = await conn.fetch("SELECT question_id, topic FROM question_topics")
        for tr in topic_rows:
            if tr["question_id"] in qid_to_meta:
                qid_to_meta[tr["question_id"]]["topics"].append(tr["topic"])

        # Company frequency map
        cf_rows = await conn.fetch(
            "SELECT question_id, SUM(COALESCE(frequency,1)) as total FROM question_companies GROUP BY question_id"
        )
        company_freq = {r["question_id"]: int(r["total"]) for r in cf_rows}

        # Build slug → appearances map
        slug_appearances: dict[str, list[dict]] = {}
        for e in all_entries:
            slug = e["slug"]
            slug_appearances.setdefault(slug, []).append(e)

        # Insert sheet_sources
        for sid, weight in SHEET_WEIGHTS.items():
            count = sheet_counts.get(sid, 0)
            await conn.execute("""
                INSERT INTO sheet_sources (id, name, problem_count, weight, fetched_at)
                VALUES ($1, $2, $3, $4, now())
                ON CONFLICT (id) DO UPDATE SET problem_count=$3, weight=$4, fetched_at=now()
            """, sid, sid.replace("_", " ").title(), count, weight)

        # Insert sheet_source_problems
        inserted_ssp = 0
        for e in all_entries:
            qid = slug_to_qid.get(e["slug"])
            if not qid:
                continue
            try:
                await conn.execute("""
                    INSERT INTO sheet_source_problems (sheet_id, question_id, position, topic_hint)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT DO NOTHING
                """, e["sheet_id"], qid, e.get("position"), e.get("topic_hint",""))
                inserted_ssp += 1
            except Exception as ex:
                pass
        print(f"[sheets] Inserted {inserted_ssp} sheet_source_problem rows")

        # Compute & insert curated mix
        print("[sheets] Computing optimal mix…")
        mix = compute_optimal_mix(slug_to_qid, qid_to_meta, slug_appearances, company_freq,
                                  fallback_corpus=True)
        print(f"[sheets] Optimal mix: {len(mix)} problems")

        await conn.execute("""
            INSERT INTO curated_sheet (id, name, description, generated_at, generator_version)
            VALUES ('optimal_mix_v1', 'AlgoSweeped Optimal Mix',
                    'Cross-sheet frequency + topic coverage + difficulty balance scoring',
                    now(), '1.1')
            ON CONFLICT (id) DO UPDATE SET generated_at=now(), generator_version='1.1'
        """)

        # Clear old mix rows then re-insert
        await conn.execute("DELETE FROM curated_sheet_problems WHERE sheet_id='optimal_mix_v1'")
        for row in mix:
            await conn.execute("""
                INSERT INTO curated_sheet_problems
                  (sheet_id, question_id, topic, ordinal, cross_sheet_count, source_sheets, score)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT DO NOTHING
            """, row["sheet_id"], row["question_id"], row["topic"],
                row["ordinal"], row["cross_sheet_count"], row["source_sheets"], row["score"])

        print(f"[sheets] Curated mix written to Supabase.")

        # Summary by topic
        topic_counts = await conn.fetch("""
            SELECT topic, count(*) FROM curated_sheet_problems
            WHERE sheet_id='optimal_mix_v1' GROUP BY topic ORDER BY topic
        """)
        for r in topic_counts:
            print(f"  {r['topic']:25s} {r['count']} problems")


if __name__ == "__main__":
    asyncio.run(main())
