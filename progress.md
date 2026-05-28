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

---

## 2026-05-28 — Intelligence-layer correctness + curated-sheet tracking (Step 3)

**Did (option 1 of the agreed 1→2→3 backlog):**
- **Step 0:** Killed the leftover duplicate vite on :5174 (PID 27156); :5173 + :8000 backend left running.
- **Bug 1 — LC tag-slugs → canonical topics.** `backend/app/services/intelligence.py`: added `LC_TAG_TO_TOPIC` (inline mirror of `scripts/lib/lc_topic_map.json`, keeps backend deploy self-contained) + `normalize_lc_topic(raw) -> Optional[str]`. `backend/app/routers/stats.py` (`_do_sync`): now aggregates `problemsSolved` by **canonical** topic (skips unmapped slugs), `DELETE FROM topic_scores WHERE user_id=:uid` once, then inserts one fresh row per canonical topic with `compute_weakness_score(canon, solved, solved)`.
- **Bug 2 — readiness `topic_coverage`.** Fixed transitively by Bug 1; `compute_readiness_score` unchanged (already matches `CORE_TOPICS` once topics are canonical).
- **Bug 3 — curated-sheet progress.** `frontend/src/types/index.ts`: added `SheetProgressMe`. `api/sheet.ts`: typed `getMySheetProgress`. `QuestionRow.tsx`: when `onStatusChange` is provided, delegate persistence to parent and skip the `question_progress` write (Questions page unchanged). `TopicAccordion.tsx`: forwards optional `onStatusChange`. `Sheet.tsx`: hydrates via `useQuery(['sheet-progress'], getMySheetProgress)`, keeps a local `overrides` map for optimism (`progress = {...progress_map, ...overrides}`), `useMutation` → `updateSheetProgress`, passes `onStatusChange` down; header count + bars now driven off `progress`. Removed dead `setProgress`.

**Result: Working — verified against live backend (user `shnavii11`).**
- `POST /stats/sync` → `GET /stats/me`: topic_scores went from **39 raw-slug rows** (`array`, `binary-tree`, `data-stream`, `brainteaser`, `line-sweep`…) to **19 canonical rows** (`arrays`=174, `trees`=116, `strings`=52…); no raw slugs remain.
- `GET /roadmap`: `weakness_score` now populated for `arrays`/`strings`/`hashing` (were `None`) + binary-search/trees/dp/graphs. (`prefix-sum` stays `None` — user simply has no solves mapped there; correct, not a bug.)
- `GET /stats/shnavii11/readiness`: `topic_coverage` **33.3 → 100.0**, total **53.0 → 73.0** (all 6 CORE_TOPICS now score > 0.5).
- Sheet round-trip: `PATCH /sheet/progress/lc-121?status=done` → `GET /sheet/progress/me` shows `done:1`. The Sheet page reads `/sheet/progress/me`, so the tracker updates immediately.
- Frontend `npm run build` (tsc + vite) type-clean.

**Note (caught during verification):** backend runs on **Python 3.9.6** (CommandLineTools), not 3.11/3.14 — PEP 604 `str | None` annotations fail at import. Used `Optional[str]` (matches existing `app/cache.py`, `app/services/llm.py` style).

**Known gaps:**
- `/stats/me` `sheet` block is Redis-cached (1h) and the sheet PATCH endpoint doesn't bust `stats:{user_id}`, so the **Dashboard** sheet number lags until cache expiry / next sync. Pre-existing pattern (`question_progress` PATCH is the same); `sheet.py` is outside Step 3's declared change surface, so left untouched — flagged for a decision.
- `compute_weakness_score` is called with `attempted = solved`, so its accuracy term is always 1.0 → the score is effectively a weighted volume metric (acceptable for now).
- Browser/visual walk-through is user-driven (not run headlessly).
- Left `lc-121` marked `done` on `shnavii11` as a verification artifact — untoggle in the UI if undesired.

**Next (agreed backlog):** Option 2 — wire the Gemini LLM (now fed correct `weak_topics`); then Option 3 — thicken the curated sheet 250 → 350–450 via sheet loaders.

---

## 2026-05-28 — Wire the Gemini LLM (Step 4, backlog option 2)

**Did (option 2 of the agreed 1→2→3 backlog):** Exposed the three bounded LLM functions in `backend/app/services/llm.py` via endpoints + Dashboard UI. They were already Redis-cached (24h) but nothing called them.
- **Model fix:** `_call_gemini` `gemini-2.0-flash-exp` → `gemini-2.0-flash`. The `-exp` experimental alias is **retired (404)**; the GA model resolves (verified via ListModels). Updated the `CLAUDE.md` LLM contract + API inventory to match.
- **Backend:**
  - `stats.py`: extracted `compute_readiness_for_user(user, db) -> dict` from `get_readiness` (no behavior change to `/stats/{username}/readiness`); reused by the new summary endpoint.
  - New `backend/app/routers/insights.py` (auth-gated, registered in `main.py`):
    - `GET /insights/readiness-summary` → `summarize_readiness(breakdown)` → `{summary,total,breakdown}`.
    - `GET /insights/recommendations` → weakest 4 topics (by `weakness_score` asc) + solved ids (question_progress ∪ sheet_progress, status='done') → `recommend_next_problems` → resolve `lc-<slug>` against `questions.slug` (LLM returns slugs; corpus id is `lc-<number>`), preserving order → `{recommendations,weak_topics}`.
    - `GET /insights/topics/{topic}/explain` → user's topic_score → `explain_topic_gap(topic, accuracy, volume)` → `{topic,explanation}`.
- **Frontend:**
  - `types/index.ts`: `RecommendedProblem`, `Recommendations`, `ReadinessSummary`, `TopicExplanation`.
  - New `api/insights.ts`: `getReadinessSummary` / `getRecommendations` / `getTopicExplanation`.
  - New `components/dashboard/RecommendedProblems.tsx`: 3-problem panel with loading skeleton + empty state.
  - `Dashboard.tsx`: auto-loads readiness-summary + recommendations on mount (own async queries, `enabled` on username); renders narrative line (hidden when empty) + the panel.
  - `TopicTable.tsx`: extracted `TopicRow` with a lazy `useQuery(getTopicExplanation, enabled:expanded)`; chevron toggles an inline explanation; row label/bar still navigate to `/questions?topic=`. (Existing sort + bar colors left unchanged — intentionally out of scope.)

**Result: Plumbing verified; live generation blocked by quota.**
- All 3 endpoints return **200** with correct shapes (dev JWT, `shnavii11`): readiness-summary `total=73.0` + breakdown; recommendations `weak_topics=['dynamic-programming','tries','segment-trees','backtracking']` (canonical, weakest-first); explain returns the topic.
- LLM **content is empty** (`summary:''`, `recommendations:[]`, `explanation:''`) because the Gemini free-tier key is **429 (daily quota exhausted)**. `llm.py` catches and returns `""/[]`, so endpoints stay 200 and the UI shows graceful "unavailable"/empty states.
- Slug-resolution path verified independently of the LLM: input `['two-sum','regular-expression-matching','same-tree']` → resolves to `lc-1/lc-10/lc-100`, preserving input order.
- Frontend `npm run build` type-clean.

**Known gaps:**
- Live LLM generations not exercised end-to-end (key 429 until quota resets, ~UTC midnight). Model name + plumbing confirmed correct; only the provider call is blocked.
- `explain_topic_gap` is fed `accuracy = solved/attempted = 1.0` (attempted==solved since Step 3), so explanations are volume-driven — unchanged known limitation.
- `/insights/readiness-summary` is current-user/auth only (no public-profile narrative yet).

**Next (agreed backlog):** Option 3 — thicken the curated sheet 250 → 350–450 via the sheet loaders / aggregation (only 2 of 16 sources currently resolve problems).
