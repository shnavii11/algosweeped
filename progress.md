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

---

## 2026-05-28 — Frontend bring-up, envelope fix & live-sync verification (Step 2)

**Did:**
- **Core fix — response envelope.** Added a response interceptor in `frontend/src/api/client.ts` that unwraps `{success, data, meta}` → `data` when both keys are present. Raw responses (`/users/me`) have no `success` key and pass through untouched. Single-point fix for all enveloped endpoints.
- **Shape reconciliation (verified against live data):**
  - `types/index.ts`: `Question.companies` is `string[]` (was `{name,frequency}[]`), and `companies`/`topics`/`number` made optional — `/questions/by-topic` and `/sheet/curated` omit them. Rewrote `StatsMe` to the real `/stats/me` shape (`user{username,last_synced}`, `snapshots{platform:{data,fetched_at}}`, `topic_scores[]`, `sheet{done,total}`). Added `PlatformSnapshot` + `ReadinessScore` types.
  - `QuestionRow.tsx`: guarded `companies` (`?? []`, render strings) — fixed a hard crash on Questions/Sheet pages (by-topic rows carry no `companies`).
  - `Sheet.tsx`: map flattened curated rows → `Question` (`id` from `question_id`), since curated rows have no nested `question`.
  - `Dashboard.tsx`: pull platform numbers from `snapshots[p].data` via a `summarize()` helper (LeetCode raw is deeply nested), and fetch readiness from `/stats/:username/readiness` (`.total`) instead of the non-existent `data.readiness_score`.
  - `api/{stats,questions,sheet}.ts`: typed `getReadiness`→`ReadinessScore`, `getQuestions`→`Question[]`, `updateSheetProgress` now sends `status` as a query param (matches backend).
- `npm run build` (tsc + vite) is type-clean.
- **Config:** filled `VITE_GITHUB_CLIENT_ID` in `frontend/.env`; renamed authStore persist key `icode-auth` → `algosweeped-auth`.
- **OAuth:** confirmed `backend/.env` already has real `GITHUB_CLIENT_SECRET`, `GITHUB_TOKEN`, `FRONTEND_URL=http://localhost:5173`, client id. Round-trip is browser-driven (not exercised headlessly here).
- **Live sync:** user `shnavii11` already had handles (lc/cf=`lokinator`, gh=`shnavii11`). Triggered `POST /stats/sync`; `last_synced` advanced within ~1s, all three fetchers wrote real data: LC 212 solved (81E/100M/31H), CF rating 809 (newbie, 6 solved), GH 22 repos / 5 recent pushes. 39 topic_scores computed. Readiness = 53.0 (dsa 51.5, github 100, coverage 33.3, sheet 0).
- **API golden-path (dev JWT, via backend):** `/users/me` raw (no envelope) ✓, `/stats/me` shape matches ✓, `/roadmap` 22 topics ✓, `/sheet/curated` 250 problems/22 topics ✓, `/sheet/sources` 16 (2 populated) ✓, `/questions/by-topic` 22 topics ✓, `/stats/:username/readiness` `{total,breakdown}` ✓.

**Result:** Frontend is type-clean and its API layer is reconciled against live backend shapes; servers run (backend :8000, vite :5173 with `/api` proxy). Live data flows.

**Known gaps:**
- Browser/visual verification and the interactive GitHub OAuth click are user-driven — not exercised headlessly.
- A duplicate vite instance is running on :5174 (leftover) — harmless; :5173 is canonical.
- Curated sheet still thin (250 vs 350–450). LLM (Gemini), Redis, and deployment unchanged.
- Sheet-page progress toggle writes to `question_progress` (via `updateQuestionProgress`), not `sheet_progress`; the sheet-specific endpoint remains unused by the UI.

**Next:** User-driven OAuth round-trip + browser page walk-through; thicken curated sheet; exercise LLM.
