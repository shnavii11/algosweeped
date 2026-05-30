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

## Step 5 — Fix weakness analytics + add test suite (2026-05-28)

### Part A — Analytics fix
- `backend/app/services/intelligence.py`: Rewrote `compute_weakness_score(topic, solved)` to `importance × (1 − mastery)` (dropped meaningless accuracy/attempted term). Added `TARGET_SOLVED=20`, `_MAX_WEIGHT`, `WEAK_THRESHOLD=0.4`. Added `aggregate_lc_topics()` extracted from `_do_sync`. Flipped `compute_readiness_score` coverage check: strong_core now counts topics with `weakness_score < WEAK_THRESHOLD` (absent → 1.0 = uncovered).
- `backend/app/routers/stats.py`: Updated import to use `aggregate_lc_topics`; `_do_sync` now calls `compute_weakness_score(canon, solved)` (2 args). Fixed `/{username}/topics` sort to `reverse=True` (weakest first = highest score first).
- `backend/app/routers/insights.py`: Changed `order_by(weakness_score.asc())` → `.desc()` so `weak_topics` fed to LLM are the genuinely weakest.
- `frontend/src/components/dashboard/TopicTable.tsx`: Replaced `{solved}/{attempted}` (always same) with `{solved} solved`.

### Part B — Test suite
- `backend/requirements.txt`: Added `pytest==8.3.4`.
- `backend/pytest.ini`: Created minimal config.
- `backend/tests/test_intelligence.py`: 18 pure tests covering `compute_weakness_score`, `normalize_lc_topic`, `compute_readiness_score`, `aggregate_lc_topics`. All green.
- `frontend/package.json` + `vite.config.ts`: Added vitest, `test` script.
- `frontend/src/api/__tests__/client.test.ts`: 5 tests for the response interceptor envelope-unwrap logic. All green.

**Verification:** `cd backend && .venv/bin/python -m pytest -q` → 18 passed. `cd frontend && npm run test` → 5 passed.

---

## 2026-05-29 — Audit + steering hardening (pre-Step 6, no app-code change)

**Did:** Full read-through of all Step 5 changes + surrounding code; re-ran every check; hardened
the steering docs; wrote the authoritative next-step plan. **No application code was changed this session.**

**Tested (all green):**
- Backend `pytest -q` → **18 passed**. Frontend `npm run test` (vitest) → **5 passed**.
- Backend imports/compiles under **Python 3.9.6** (`py_compile` on insights/stats/roadmap/sheet/questions;
  `import intelligence` runs). Spot-checked the new metric live: `compute_weakness_score('graphs',0)=0.9286`
  (=1.3/1.4), `('arrays',20)=0.0`. ✓
- Frontend typecheck: **`./node_modules/.bin/tsc --noEmit` clean.** (Gotcha: `npx tsc` installs a *bogus*
  `tsc@2.0.4` package — always use the local binary or `npm run build`.)

**Audit result — Step 5 shipped correctly.** Weakness metric, readiness-coverage flip, sort direction
(`.desc()`/`reverse=True`), and `TopicTable` colors are all internally consistent under "higher = weaker".

**Bugs found (none are Step 5 regressions; all pre-existing — queued into `step6.md`):**
1. **`insights.py:90` still feeds bogus 100% accuracy to the LLM.** `attempted==solved` + `accuracy=None`
   ⇒ `solved/max(attempted,1)` is always `1.0`. The exact bug Step 5 killed in scoring, still leaking into
   the topic-gap prompt. → Fix 3.
2. **`sheet.py` PATCH doesn't bust `stats:`/`readiness:`** (1h stale window on the Dashboard). → Fix 2.
3. **`questions.py` PATCH doesn't bust `roadmap:{uid}`** — *new finding.* `roadmap.py` derives
   `user_solved`/`user_attempted` from `question_progress` and caches under `roadmap:{uid}` (1h), so the
   Roadmap page lags. This **corrects `step5.md`**, which claimed `question_progress` only feeds the
   (LLM-cached) recommendations and so `questions.py` needed no bust. → Fix 4.
4. **`Profile.tsx` ignores the `:username` route param** (always shows own data; `getPublicProfile` not wired). → Fix 1.
- Minor/pre-existing (backlog, not fixing): `llm.py` groq branch uses `gemini_api_key` for auth; recommend
  cache key truncates `solved_ids[:20]`; `@vitest/ui` devDep unused.

**Steering hardening — `CLAUDE.md` (the single source of truth was contradicting reality):**
- **Runtime:** table said "Python 3.11"; actual dev venv is **3.9.6**. Added a **Runtime Reality & Coding
  Gotchas** section (no PEP 604 unions; `attempted==solved` is a placeholder so accuracy is meaningless;
  `LC_TAG_TO_TOPIC` is an inline mirror to keep in sync; requirements pins are 3.14-era). This contradiction
  had already bitten twice (Steps 3 & 5).
- Added **Scoring Semantics** (weakness higher=weaker, formula, descending sort, readiness coverage rule)
  and **Tests** (commands + keep-green) sections.
- Fixed the repo-root name (`icode-plus/` → `name_that_folder/`) and added the **plan-file numbering
  convention** (`stepN.md`'s N = the `progress.md` Step N it becomes; legacy step4/step5 are offset by one).

**Next-step plan:** wrote **`step6.md`** (authoritative; supersedes `step5.md`, which now carries a pointer
banner). Covers Fixes 1–4 + live E2E browser walk-through. **What worked:** the hermetic test suite made the
audit fast and trustworthy; reading `roadmap.py` end-to-end is what surfaced the cache bug the prior plan
missed. **What didn't change:** no app code touched — fixes deliberately deferred to the Step 6 coding pass
so they land with their E2E verification.

**Next:** code Step 6 (`step6.md`).


## Step 6 (Part 0) — Insights resilience fix (2026-05-30)
Diagnosed dashboard "No recommendations available" + "Explanation unavailable": Gemini 429
(quota) + llm.py caching empty failures 24h + no non-LLM fallback. Shipped: stop caching empty
results; corpus fallback for /insights/recommendations; deterministic fallbacks for topic-explain
and readiness-summary. 21 backend tests green. Remaining step6 items (Public Profile, cache-bust,
accuracy proxy) still backlog as Part 1.


## Step 7 (Part 1) — The four Step-6 Part-1 bug fixes (2026-05-30)
Coded the four deferred fixes from `step6.md`/`step7.md`. All tests green (21 backend, 5 frontend, tsc clean).

1. **Public Profile page (Fix 1).** `Profile.tsx` now reads the `:username` route param: own profile
   (no param or matches `me.username`) keeps the editable view; another username fetches
   `getPublicProfile()` → `GET /users/{username}/public` and renders a **read-only** card (no edit button),
   showing GitHub via `github_login`. 404 → "User not found" card. Added `getPublicProfile` to `api/auth.ts`
   and optional `github_login?: string` to the `User` type (UserPublic's field name differs from `gh_username`).
2. **Sheet progress cache-bust (Fix 2).** `sheet.py` `update_sheet_progress` now imports `delete_cached` and
   busts `stats:{uid}` + `readiness:{uid}` after commit, so the Dashboard's `sheet.done`/readiness update now.
3. **Topic-gap mastery proxy (Fix 3).** `insights.py` `explain_topic` no longer feeds the bogus
   `solved/max(attempted,1) == 1.0` accuracy to the LLM; it passes `mastery = round(1 - weakness_score, 2)`.
   `llm.explain_topic_gap` param renamed `accuracy → mastery`, prompt reworded to "≈{mastery*100}% of a target
   baseline", cache-key field renamed to `mastery`. No test referenced the old prompt/key.
4. **Question progress roadmap cache-bust (Fix 4).** `questions.py` `update_progress` now imports
   `delete_cached` and busts `roadmap:{uid}` after commit (NOT stats:/readiness: — `question_progress`
   doesn't feed them), so the Roadmap page's `user_solved` updates now.

**Next:** Part 2 (curated-sheet thickening 250→350–450), Part 3 (E2E browser walk), Part 4 (cleanup).
