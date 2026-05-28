"""
Download open-source company-tag datasets and merge into question_companies table.

Sources (tried in order, all merged together):
  1. krishnadey30/LeetCode-Questions-CompanyWise
  2. liquidslr/leetcode-company-wise-problems
  3. hxu296/leetcode-company-wise-problems-2022
  4. seanprashad/leetcode-patterns  (patterns overlay)
"""
import asyncio
import csv
import io
import json
import sys
import zipfile
from pathlib import Path

import httpx

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lib.db import connection
from lib.upsert import upsert_question_companies

# Map of slug → [{name, frequency, timeframe}]
CompanyMap = dict[str, list[dict]]

SOURCES = [
    {
        "id": "krishnadey30",
        "zip_url": "https://github.com/krishnadey30/LeetCode-Questions-CompanyWise/archive/refs/heads/master.zip",
        "timeframes": ["6months", "1year", "2years"],
        "csv_col_question": 0,
        "csv_col_freq": None,
    },
    {
        "id": "liquidslr",
        "zip_url": "https://github.com/liquidslr/leetcode-company-wise-problems/archive/refs/heads/main.zip",
        "timeframes": ["all"],
        "csv_col_question": 1,
        "csv_col_freq": None,
    },
    {
        "id": "hxu296",
        "zip_url": "https://github.com/hxu296/leetcode-company-wise-problems-2022/archive/refs/heads/main.zip",
        "timeframes": ["all"],
        "csv_col_question": 0,
        "csv_col_freq": 1,
    },
]

SEANPRASHAD_URL = "https://raw.githubusercontent.com/seanprashad/leetcode-patterns/master/src/data/data.json"


def normalise_slug(raw: str) -> str:
    s = raw.strip().lower().replace(" ", "-").replace("_", "-")
    # strip leading problem number if present
    parts = s.split("-")
    if parts and parts[0].isdigit():
        s = "-".join(parts[1:])
    return s


async def fetch_zip_source(client: httpx.AsyncClient, source: dict) -> CompanyMap:
    result: CompanyMap = {}
    try:
        resp = await client.get(source["zip_url"], timeout=60, follow_redirects=True)
        z = zipfile.ZipFile(io.BytesIO(resp.content))
        for name in z.namelist():
            if not name.endswith(".csv"):
                continue
            parts = name.split("/")
            # company name is typically the folder or file name
            company = parts[-2] if len(parts) > 2 else parts[-1].replace(".csv", "")
            company = company.replace("-", " ").replace("_", " ").title()

            timeframe = "all"
            for tf in source.get("timeframes", ["all"]):
                if tf in name.lower():
                    timeframe = tf
                    break

            content = z.read(name).decode("utf-8", errors="ignore")
            reader = csv.reader(io.StringIO(content))
            next(reader, None)  # skip header
            for row in reader:
                if not row:
                    continue
                qcol = source["csv_col_question"]
                if qcol >= len(row):
                    continue
                slug = normalise_slug(row[qcol])
                freq_col = source.get("csv_col_freq")
                freq = None
                if freq_col is not None and freq_col < len(row):
                    try:
                        freq = int(row[freq_col])
                    except ValueError:
                        pass
                result.setdefault(slug, [])
                result[slug].append({"name": company, "frequency": freq, "timeframe": timeframe})
    except Exception as e:
        print(f"[companies] Source {source['id']} failed: {e}")
    return result


async def fetch_seanprashad(client: httpx.AsyncClient) -> CompanyMap:
    result: CompanyMap = {}
    try:
        resp = await client.get(SEANPRASHAD_URL, timeout=30)
        data = resp.json()
        problems = data if isinstance(data, list) else data.get("data", [])
        for p in problems:
            slug = normalise_slug(p.get("url", "").rstrip("/").split("/")[-1] or p.get("title", ""))
            companies = p.get("companies", [])
            for c in companies:
                result.setdefault(slug, [])
                result[slug].append({"name": c, "frequency": None, "timeframe": "all"})
    except Exception as e:
        print(f"[companies] SeanPrashad failed: {e}")
    return result


def merge_maps(*maps: CompanyMap) -> CompanyMap:
    merged: CompanyMap = {}
    for m in maps:
        for slug, entries in m.items():
            merged.setdefault(slug, [])
            for e in entries:
                # deduplicate by (company, timeframe)
                key = (e["name"], e["timeframe"])
                existing = {(x["name"], x["timeframe"]) for x in merged[slug]}
                if key not in existing:
                    merged[slug].append(e)
    return merged


async def main():
    print("[companies] Fetching open-source company datasets…")
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[fetch_zip_source(client, src) for src in SOURCES],
            fetch_seanprashad(client),
        )

    merged = merge_maps(*results)
    total_slugs = len(merged)
    total_entries = sum(len(v) for v in merged.values())
    print(f"[companies] Merged: {total_slugs} slugs, {total_entries} company entries")

    # Write to DB — only for slugs that already exist in questions
    async with connection() as conn:
        rows = await conn.fetch("SELECT id, slug FROM questions WHERE platform='leetcode' AND slug IS NOT NULL")
        slug_to_id = {r["slug"]: r["id"] for r in rows}

        written = 0
        for slug, entries in merged.items():
            qid = slug_to_id.get(slug)
            if not qid:
                continue
            await upsert_question_companies(conn, qid, entries)
            written += len(entries)

        print(f"[companies] Wrote {written} company entries for {len(slug_to_id)} LC problems")

    # Save local reference
    out = ROOT / "data" / "sheets" / "companies_merged.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(merged, f)
    print(f"[companies] Saved reference to {out}")


if __name__ == "__main__":
    asyncio.run(main())
