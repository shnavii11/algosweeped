"""
Validate corpus integrity against live Supabase tables.
Exits with code 1 if any critical check fails.
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.db import connection

REQUIRED_TOPICS = [
    "arrays","strings","hashing","two-pointers","sliding-window","prefix-sum",
    "binary-search","linked-list","stacks-queues","recursion","backtracking",
    "trees","bst","heap","greedy","dynamic-programming","graphs","tries",
    "segment-trees","bit-manipulation","math","string-algorithms",
]

CHECKS_FAILED = 0


def check(name: str, passed: bool, detail: str = ""):
    global CHECKS_FAILED
    status = "PASS" if passed else "FAIL"
    mark = "✓" if passed else "✗"
    print(f"  [{status}] {mark} {name}" + (f": {detail}" if detail else ""))
    if not passed:
        CHECKS_FAILED += 1


async def main():
    print("\n[validate] Running corpus integrity checks…\n")
    async with connection() as conn:

        # 1. Tables exist and have rows
        q_count = await conn.fetchval("SELECT count(*) FROM questions")
        check("questions table populated", q_count > 0, f"{q_count} rows")

        lc_count = await conn.fetchval("SELECT count(*) FROM questions WHERE platform='leetcode'")
        check("LeetCode problems present", lc_count > 100, f"{lc_count} rows")

        cf_count = await conn.fetchval("SELECT count(*) FROM questions WHERE platform='codeforces'")
        check("Codeforces problems present", cf_count > 100, f"{cf_count} rows")

        qt_count = await conn.fetchval("SELECT count(*) FROM question_topics")
        check("question_topics populated", qt_count > 0, f"{qt_count} rows")

        # 2. No question with NULL id or title
        null_ids = await conn.fetchval("SELECT count(*) FROM questions WHERE id IS NULL OR title IS NULL OR title=''")
        check("No null id/title", null_ids == 0, f"{null_ids} bad rows")

        # 3. No duplicate question IDs
        dup = await conn.fetchval("SELECT count(*) FROM (SELECT id, count(*) FROM questions GROUP BY id HAVING count(*)>1) x")
        check("No duplicate question IDs", dup == 0, f"{dup} duplicates")

        # 4. Every question_topics.topic maps to roadmap_topics
        orphan_topics = await conn.fetchval("""
            SELECT count(DISTINCT qt.topic)
            FROM question_topics qt
            LEFT JOIN roadmap_topics rt ON rt.topic = qt.topic
            WHERE rt.topic IS NULL
        """)
        check("All question topics in roadmap", orphan_topics == 0, f"{orphan_topics} unmapped topics")

        # 5. All 22 roadmap topics present
        rt_count = await conn.fetchval("SELECT count(*) FROM roadmap_topics")
        check("All 22 roadmap topics seeded", rt_count >= 22, f"{rt_count} topics")

        # 6. Curated sheet exists with problems
        mix_count = await conn.fetchval(
            "SELECT count(*) FROM curated_sheet_problems WHERE sheet_id='optimal_mix_v1'"
        )
        check("Curated mix has problems", mix_count > 50, f"{mix_count} problems")

        # 7. Every required topic in curated mix
        for topic in REQUIRED_TOPICS:
            tc = await conn.fetchval(
                "SELECT count(*) FROM curated_sheet_problems WHERE sheet_id='optimal_mix_v1' AND topic=$1",
                topic
            )
            check(f"  mix topic: {topic}", tc > 0, f"{tc} problems")

        # 8. Sheet sources recorded
        src_count = await conn.fetchval("SELECT count(*) FROM sheet_sources")
        check("Sheet sources recorded", src_count > 0, f"{src_count} sources")

        # 9. Fetch runs recorded
        run_count = await conn.fetchval("SELECT count(*) FROM fetch_runs WHERE status='ok'")
        check("Successful fetch runs recorded", run_count > 0, f"{run_count} runs")

        print(f"\n[validate] {'ALL CHECKS PASSED' if CHECKS_FAILED == 0 else f'{CHECKS_FAILED} CHECKS FAILED'}\n")

    sys.exit(0 if CHECKS_FAILED == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
