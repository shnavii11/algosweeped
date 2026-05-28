"""Export questions and curated sheet from Supabase to data/snapshots/ for audit."""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.db import connection

SNAP_DIR = ROOT / "data" / "snapshots"
SNAP_DIR.mkdir(parents=True, exist_ok=True)


async def main():
    today = datetime.utcnow().strftime("%Y%m%d")
    async with connection() as conn:
        for platform in ("leetcode", "codeforces"):
            rows = await conn.fetch(
                "SELECT id, platform, number, title, slug, url, difficulty, difficulty_rating, "
                "       is_premium, acceptance_rate, solved_count, fetched_at "
                "FROM questions WHERE platform=$1 ORDER BY id",
                platform
            )
            data = [dict(r) for r in rows]
            # Convert datetime objects
            for d in data:
                if d.get("fetched_at"):
                    d["fetched_at"] = d["fetched_at"].isoformat()
            path = SNAP_DIR / f"{platform}_{today}.json"
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            print(f"[export] {platform}: {len(data)} problems → {path}")

        # Export curated mix
        mix_rows = await conn.fetch("""
            SELECT csp.question_id, csp.topic, csp.ordinal, csp.cross_sheet_count,
                   csp.source_sheets, csp.score,
                   q.title, q.difficulty, q.url
            FROM curated_sheet_problems csp
            JOIN questions q ON q.id = csp.question_id
            WHERE csp.sheet_id = 'optimal_mix_v1'
            ORDER BY csp.topic, csp.ordinal
        """)
        mix_data = [dict(r) for r in mix_rows]
        mix_path = SNAP_DIR / f"curated_mix_{today}.json"
        with open(mix_path, "w") as f:
            json.dump(mix_data, f, indent=2)
        print(f"[export] curated mix: {len(mix_data)} problems → {mix_path}")

        # Write provenance file
        prov = {
            "exported_at": datetime.utcnow().isoformat(),
            "leetcode_count": len([r for r in mix_rows]) and await conn.fetchval("SELECT count(*) FROM questions WHERE platform='leetcode'"),
            "codeforces_count": await conn.fetchval("SELECT count(*) FROM questions WHERE platform='codeforces'"),
            "curated_mix_count": len(mix_data),
            "fetch_runs": [dict(r) for r in await conn.fetch(
                "SELECT platform, layer, status, problem_count, finished_at FROM fetch_runs ORDER BY finished_at DESC LIMIT 10"
            )],
        }
        for r in prov["fetch_runs"]:
            if r.get("finished_at"):
                r["finished_at"] = r["finished_at"].isoformat()
        with open(ROOT / "data" / "_fetched_at.json", "w") as f:
            json.dump(prov, f, indent=2)
        print(f"[export] Provenance → data/_fetched_at.json")


if __name__ == "__main__":
    asyncio.run(main())
