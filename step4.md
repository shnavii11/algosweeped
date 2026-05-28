# Step 4 (file) — Fix the weakness analytics, then add a test suite

> Note: `progress.md` already logged the Gemini LLM work as its "Step 4" entry; this spec
> file is the *next* build step (it will be logged as Step 5 in `progress.md`/`memory.md`).
> Named `step4.md` to follow the `step3.md` file convention.

## Context

A project audit (two Explore passes) found the app's **headline feature is semantically broken**. `topic_scores` are stored with `attempted == solved` (`backend/app/routers/stats.py` `_do_sync`), so the accuracy term — 70% of `compute_weakness_score` (`backend/app/services/intelligence.py`) — is always `1.0`. The result is that `weakness_score` actually measures **strength** (higher = more mastery), the field name is therefore a lie, and `compute_readiness_score` + `insights.py` recommendations + the Dashboard table all consume it under the wrong assumption. The audit also found the project has **zero automated tests**.

The user chose to **(1) fix the weakness analytics** and **(4) add a test suite** now (fix first, so the tests encode the corrected behavior), and to **add (2) end-to-end browser verification + loose-end fixes to the backlog** after. This step = parts A + B below.

**Key insight that keeps the change small:** we don't rename anything. Making the metric genuinely measure weakness (higher = weaker) makes the existing name `weakness_score` *correct*, and makes the existing Dashboard `TopicTable` colors (`>0.7` red) and descending sort *correct* — no DB migration, no rename cascade. True per-topic accuracy isn't available from LeetCode's public data (`tagProblemCounts` gives solved-per-tag only), so weakness is honestly redefined as **topic importance × lack of coverage**, not invented accuracy.

## Part A — Fix the weakness analytics

### A1. `backend/app/services/intelligence.py` — redefine the metric (higher = weaker)
- Add `TARGET_SOLVED = 20` and `_MAX_WEIGHT = max(TOPIC_WEIGHTS.values())`.
- Rewrite `compute_weakness_score(topic: str, solved: int) -> float` (drop the meaningless `attempted`/accuracy term):
  ```
  mastery    = min(solved / TARGET_SOLVED, 1.0)            # coverage of the topic
  importance = TOPIC_WEIGHTS.get(topic, 1.0) / _MAX_WEIGHT  # 0..1, DP/graphs weigh most
  return round(importance * (1.0 - mastery), 4)            # 0 (mastered) .. ~1 (weak+important)
  ```
- `compute_readiness_score`: flip the coverage test — a core topic now counts as covered when weakness is **low**:
  `strong_core = sum(1 for ts in topic_scores if ts["topic"] in CORE_TOPICS and (ts.get("weakness_score") if ts.get("weakness_score") is not None else 1.0) < WEAK_THRESHOLD)` with `WEAK_THRESHOLD = 0.4` (absent topic defaults to 1.0 = not covered). No other readiness math changes.

### A2. `backend/app/routers/stats.py`
- `_do_sync`: call `compute_weakness_score(canon, solved)` (new 2-arg signature). Leave the `attempted=solved` column write as-is (no real attempted data; out of scope) — but it stops feeding the score.
- `GET /{username}/topics`: the existing `rows.sort(key=lambda x: x.get("weakness_score") or 1.0)` now sorts strongest-first; change to **descending** so weakest-first stays the contract (`reverse=True`, missing → `-1`). Minor consistency fix.

### A3. `backend/app/routers/insights.py`
- `recommendations`: change `order_by(TopicScore.weakness_score.asc())` → `.desc()` so `weak_topics` are the genuinely weakest topics fed to `recommend_next_problems` (better LLM signal).

### A4. `frontend/src/components/dashboard/TopicTable.tsx`
- Colors (`>0.7` red / `>0.4` amber / else green) and the descending sort are now **correct** under the flipped semantics — leave them.
- Replace the misleading `{solved}/{attempted}` readout (renders e.g. `174/174`) with a plain `{solved} solved` count. No other UI change.

## Part B — Add a test suite (hermetic: no Supabase / Redis / Gemini)

### B1. Backend (pytest) — the high-value target
- Add `pytest` (+ `pytest-asyncio` only if needed) to `backend/requirements.txt`; add minimal `backend/pytest.ini` (or `[tool.pytest.ini_options]`).
- **Extract one pure helper for testability:** move the LC tag→canonical aggregation out of `_do_sync` into `intelligence.aggregate_lc_topics(tag_problem_counts: dict) -> Dict[str,int]` and call it from `_do_sync`. Small, justified refactor.
- `backend/tests/test_intelligence.py` (pure, sync, no I/O):
  - `compute_weakness_score`: more solved → lower weakness; ≥`TARGET_SOLVED` → ~0; higher-weight topic → higher weakness at equal solves; output bounded `[0,1]`.
  - `normalize_lc_topic`: representative slugs map to canonical (`binary-tree`→`trees`, `brainteaser`→`math`); unknown → `None`.
  - `compute_readiness_score`: breakdown keys + math; coverage uses the new `< WEAK_THRESHOLD` rule (well-covered core → high coverage; sparse core → low).
  - `aggregate_lc_topics`: collapses multiple raw slugs onto one canonical topic and sums; skips unmapped.

### B2. Frontend (Vitest) — minimal, highest-signal
- Add `vitest` devDep + `test` script + config (jsdom not required for this).
- `frontend/src/api/__tests__/client.test.ts`: assert the response interceptor in `src/api/client.ts` unwraps `{success,data,meta}` → `data` and passes a raw body (no `success` key, e.g. `/users/me`) through untouched. Mock axios; no network.

## Verification
- **Backend tests:** `cd backend && .venv/bin/python -m pytest -q` → all green (Python 3.9 runtime — no PEP 604 `X | None` in test or source; use `Optional`/`Dict`).
- **Analytics live re-check** (server auto-reloads; dev JWT for `shnavii11`): `POST /stats/sync` → `GET /stats/me` shows `weakness_score` now **high for sparse topics, low for well-covered** (e.g. `arrays`≈0, an under-solved core topic high); `GET /stats/shnavii11/readiness` `topic_coverage` recomputes to a sensible value (will differ from the old 100 — expected, now honest); `GET /insights/recommendations` `weak_topics` are the weakest (highest-score) topics.
- **Frontend:** `npm run test` green; `npm run build` type-clean; `TopicTable` shows weakest topics on top with red bars and a `N solved` readout.
- Append Step 5 to `progress.md` + `memory.md`; update persistent backlog memory. Commit; **ask before pushing**.

## Backlog (recorded, not done this step)
- **Option 2 — verify end-to-end + fix loose ends (NEXT after this):** run the full app in a browser via an injected dev JWT (bypassing the GitHub OAuth click), walk every page against live data, and fix the two concrete bugs found: (a) the **public Profile page** — `frontend/src/pages/Profile.tsx` ignores the `:username` route param and never calls `GET /users/:username/public`; (b) **stats cache staleness** — `PATCH /sheet/progress/:id` (`routers/sheet.py`) and `PATCH /questions/:id/progress` (`routers/questions.py`) don't `delete_cached(f"stats:{user_id}")`.
- Deferred (unchanged): deployment (Vercel + Railway), thicken curated sheet 250→350–450, live Gemini run once quota resets.

## Critical files
- Backend: `backend/app/services/intelligence.py`, `backend/app/routers/stats.py`, `backend/app/routers/insights.py`, `backend/requirements.txt`, **new** `backend/pytest.ini`, **new** `backend/tests/test_intelligence.py`.
- Frontend: `frontend/src/components/dashboard/TopicTable.tsx`, `frontend/package.json` (+ vitest config), **new** `frontend/src/api/__tests__/client.test.ts`.
- Meta: `progress.md`, `memory.md`, persistent memory.
