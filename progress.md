# AlgoSweeped — Build Progress Log

Append-only. Each entry records one discrete step.

---

## 2026-05-26 — Repository initialized

**Did:** Created git repo, full directory tree, CLAUDE.md, progress.md, memory.md, README.md, db/migrations/0001_init.sql, backend/.env.example, backend/requirements.txt.

**Result:** Working

**Next:** Collect Supabase keys from user → run migration → run scrapers

---

## 2026-05-28 — Data layer audit + Backend bring-up (Step 1)

**Did:**
- Audited true state of repo: data layer (implementation plan steps 0–3) was already complete but never recorded.
- **Schema (step 0):** All 14 Supabase tables present.
- **Corpus (step 1):** 15,160 questions (3,944 LC via `rest_all`, 11,216 CF via `official_api`), 36,362 topic links, 10,016 company tags. `fetch_runs` has 5 `ok` rows.
- **Sheets + curated mix (step 2):** 16 `sheet_sources`, 250 `curated_sheet_problems` (target 350–450 — thin, deferred).
- **Roadmap (step 3):** 22 `roadmap_topics` present.
- Fixed `.gitignore`: added `data/*.json` and `.claude/settings.local.json`.
- Installed FastAPI backend deps on Python 3.14 (bumped all pins); updated `backend/requirements.txt`.
- Booted uvicorn server; confirmed 27 routes loaded cleanly against live Supabase.
- Smoke-tested all read endpoints: `/health`, `/questions`, `/questions/by-topic`, `/sheet/curated` (250 problems / 22 topics), `/sheet/sources` (16), `/roadmap` (22 ordered topics via minted JWT).
- Made first git commit and pushed to `https://github.com/shnavii11/name_that_folder.git`.

**Result:** Backend verified. All public + auth-gated read endpoints return live Supabase data.

**Known gaps:**
- Curated sheet: 250 problems vs 350–450 target — sheet loaders only resolved 250 source entries. Deferred.
- Frontend: `node_modules` present, not yet verified against running backend.

**Next:** Frontend bring-up and verification (step 5).
