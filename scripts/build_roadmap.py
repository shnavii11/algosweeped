"""
Populate roadmap_topics with starter + milestone problems
drawn from the curated mix and the question corpus.
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.db import connection

TOPIC_ORDER = [
    "arrays","strings","hashing","two-pointers","sliding-window","prefix-sum",
    "binary-search","linked-list","stacks-queues","recursion","backtracking",
    "trees","bst","heap","greedy","dynamic-programming","graphs","tries",
    "segment-trees","bit-manipulation","math","string-algorithms",
]

with open(ROOT / "scripts/lib/topic_editorial.json") as f:
    EDITORIAL: dict = json.load(f)


async def main():
    print("[roadmap] Building roadmap topic entries…")
    async with connection() as conn:
        for topic in TOPIC_ORDER:
            ed = EDITORIAL.get(topic, {})

            # Starter: easiest 3 problems from curated mix for this topic
            starter_rows = await conn.fetch("""
                SELECT csp.question_id, q.difficulty, q.url
                FROM curated_sheet_problems csp
                JOIN questions q ON q.id = csp.question_id
                WHERE csp.sheet_id = 'optimal_mix_v1' AND csp.topic = $1
                ORDER BY
                  CASE q.difficulty WHEN 'easy' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                  csp.score DESC
                LIMIT 3
            """, topic)
            starter_ids = [r["question_id"] for r in starter_rows]

            # Milestone: top 3 by company frequency for this topic
            milestone_rows = await conn.fetch("""
                SELECT qt.question_id, SUM(COALESCE(qc.frequency,1)) AS cf
                FROM question_topics qt
                LEFT JOIN question_companies qc ON qc.question_id = qt.question_id
                WHERE qt.topic = $1
                GROUP BY qt.question_id
                ORDER BY cf DESC
                LIMIT 3
            """, topic)
            milestone_ids = [r["question_id"] for r in milestone_rows]

            await conn.execute("""
                UPDATE roadmap_topics SET
                  summary            = COALESCE($2, summary),
                  core_patterns      = COALESCE($3, core_patterns),
                  starter_problems   = $4,
                  milestone_problems = $5
                WHERE topic = $1
            """, topic,
                ed.get("summary"),
                ed.get("core_patterns"),
                starter_ids or None,
                milestone_ids or None,
            )
            print(f"  {topic:25s} starters={len(starter_ids)}  milestones={len(milestone_ids)}")

    print("[roadmap] Done.")


if __name__ == "__main__":
    asyncio.run(main())
