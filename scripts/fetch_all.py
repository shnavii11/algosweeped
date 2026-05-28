"""
Master orchestrator. Run once before building the app.

Usage:
  python scripts/fetch_all.py
  python scripts/fetch_all.py --skip-lc        # skip LeetCode (reuse existing)
  python scripts/fetch_all.py --skip-cf        # skip Codeforces
  python scripts/fetch_all.py --skip-sheets    # skip sheet aggregation
  python scripts/fetch_all.py --dry-run --break-layer graphql  # test fallback
"""
import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_codeforces
import fetch_leetcode
import aggregate_sheets
import build_roadmap
import validate_corpus
import export_snapshots


async def main(args):
    print("=" * 60)
    print("AlgoSweeped corpus fetch — start")
    print("=" * 60)

    if not args.skip_lc:
        print("\n── Step 1: LeetCode ──────────────────────────────────────")
        await fetch_leetcode.main()
    else:
        print("\n── Step 1: LeetCode (SKIPPED) ───────────────────────────")

    if not args.skip_cf:
        print("\n── Step 2: Codeforces ────────────────────────────────────")
        await fetch_codeforces.main()
    else:
        print("\n── Step 2: Codeforces (SKIPPED) ─────────────────────────")

    if not args.skip_sheets:
        print("\n── Step 3: Companies enrichment ─────────────────────────")
        from enrich_companies import main as enrich_main
        await enrich_main()

        print("\n── Step 4: Sheet aggregation + optimal mix ───────────────")
        await aggregate_sheets.main()

        print("\n── Step 5: Roadmap builder ───────────────────────────────")
        await build_roadmap.main()
    else:
        print("\n── Steps 3-5: Sheets + Roadmap (SKIPPED) ────────────────")

    print("\n── Step 6: Validate corpus ───────────────────────────────")
    await validate_corpus.main()

    print("\n── Step 7: Export snapshots ──────────────────────────────")
    await export_snapshots.main()

    print("\n" + "=" * 60)
    print("AlgoSweeped corpus fetch — complete")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-lc", action="store_true")
    parser.add_argument("--skip-cf", action="store_true")
    parser.add_argument("--skip-sheets", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--break-layer", default="")
    args = parser.parse_args()

    if args.dry_run:
        print(f"DRY RUN mode — would break layer: {args.break_layer or 'none'}")
        sys.exit(0)

    asyncio.run(main(args))
