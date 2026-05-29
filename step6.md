# Step 6 (next build step) — E2E verification + fix the loose ends found by audit

> **Supersedes `step5.md`** (same intent, renumbered to match `progress.md` Step 6, and
> adds Fix 4 — the roadmap cache bug that `step5.md`'s analysis missed). This is backlog
> **Option 2** ("verify end-to-end + fix loose ends"), now current.
> Numbering convention going forward: `stepN.md`'s N = the `progress.md` "Step N" it becomes.

## Audit of Step 5 (weakness-fix + test suite) — result: CLEAN, shipped correctly

Re-verified this session (2026-05-29). All Step 5 changes are sound:
- `compute_weakness_score(topic, solved) = importance × (1 − mastery)` — bounded `[0,1]`, monotonic,
  `0` at `TARGET_SOLVED=20`. Spot-checked live: `graphs@0 = 0.9286 (=1.3/1.4)`, `arrays@20 = 0.0`. ✓
- `compute_readiness_score` coverage flipped to `weakness < 0.4`, absent core topic → 1.0 (uncovered). ✓
- `stats.py /topics` sort `reverse=True` + `insights.py order_by(.desc())` consistent with "higher = weaker". ✓
- `TopicTable.tsx` colors/sort/`{solved} solved` readout consistent. ✓
- **18 backend pytest + 5 frontend vitest green**; backend imports/compiles under Python 3.9.6; `tsc --noEmit` clean. ✓

## Part 0 — Insights resilience bug fix  *(DONE 2026-05-30 — do first, shipped)*

**Symptom (from dashboard screenshots):** "Recommended Next Problems" shows *"No
recommendations available right now."* and every expanded topic under "Topic Weakness
Analysis" shows *"Explanation unavailable right now."*

**Root cause (reproduced):** the **Gemini free-tier quota is exhausted** — the live endpoint
returns **HTTP 429** on every call (confirmed across retries). `_call_gemini` does
`raise_for_status()`, so all three `llm.py` functions catch and return `[]`/`""`, and the cards
render the "unavailable" placeholders.
*(Note: `cache.py` already degrades gracefully — `get_cached`/`set_cached` guard `if not r`.
There is no `redis_client`/`_CacheProxy`; Redis was **not** the cause.)*

**Compounding bug:** `llm.py` cached the empty/failed result with a 24h TTL (`set_cached`
unconditionally), so a transient 429 kept the cards blank for a full day even after quota reset.

**Fixes shipped:**
1. `backend/app/services/llm.py` — only `set_cached` when the result is non-empty, in all three
   functions. A 429/outage no longer poisons the cache.
2. `backend/app/routers/insights.py` `recommendations` — when LLM ids resolve to `< 3` problems,
   top up from the corpus: `questions JOIN question_topics` on the user's weak topics, excluding
   solved + non-premium, ordered by `acceptance_rate DESC`. The card is never empty even with the
   LLM down.
3. `backend/app/routers/insights.py` `explain_topic` — when the LLM returns `""`, build a
   deterministic paragraph from the weakness band + solved volume + `roadmap_topics.summary`/
   `core_patterns` (`_fallback_topic_explanation`).
4. `backend/app/routers/insights.py` `readiness_summary` — when the LLM returns `""`, build a
   templated narrative from the score breakdown (`_fallback_readiness_summary`).
5. `backend/tests/test_intelligence.py` — 3 new pure tests (slug formatting; empty result not
   cached on failure for recommend + summarize). **21 backend tests green.**

**Verify live:** with Gemini still 429, the recommendations card now lists real corpus problems
and topic explanations show the deterministic diagnosis; once quota resets the LLM text returns
automatically (no longer stuck behind a 24h cached empty).

---

## Part 1 — remaining loose ends (backlog, NOT done this session)

### Fix 1 — Public Profile page ignores the `:username` route param  *(confirmed)*
`App.tsx` routes `/profile/:username?` → `Profile.tsx`, but `Profile.tsx` only ever calls `getMe()`.
Visiting `/profile/<someone-else>` shows **your own** data; backend `GET /users/{username}/public`
(exists, returns `UserPublic`) is never called from the frontend.

Plan:
- `frontend/src/api/auth.ts`: add
  `export const getPublicProfile = (username: string) => client.get<User>(\`/users/${username}/public\`).then(r => r.data)`.
- `frontend/src/pages/Profile.tsx`:
  - `const { username } = useParams()`; always `getMe()` to know own username (cheap, cached).
  - **Own** (`!username || username === me.username`): keep current editable view.
  - **Public** (`username !== me.username`): `useQuery(['public', username], () => getPublicProfile(username))`,
    render **read-only** (no "Edit platforms" button, no form).
  - 404 → simple "User not found" card.
- Field note: `UserPublic` exposes **`github_login`** (id, username, name, college, avatar_url, github_login,
  lc_username, cf_handle, created_at) — *not* `gh_username`. Show GitHub via `github_login` in the public view.
  (Confirmed against `backend/app/schemas/user.py`.)

### Fix 2 — Stats/readiness cache not busted on sheet progress write  *(confirmed)*
`PATCH /sheet/progress/{problem_id}` (`routers/sheet.py`) commits but never invalidates `stats:{uid}`
(caches `sheet.done/total`, 1h) or `readiness:{uid}` (reads `sheet_progress`, 1h). Marking a problem
done won't show in Dashboard stats/readiness for up to an hour. (`sheet.py` doesn't even import `delete_cached`.)

Plan:
- `routers/sheet.py`: import `delete_cached` from `..cache`; after the commit in `update_sheet_progress`,
  `await delete_cached(f"stats:{current_user.id}")` and `await delete_cached(f"readiness:{current_user.id}")`.

### Fix 3 — `insights.py` topic-gap still feeds bogus 100% accuracy to the LLM  *(confirmed — the exact bug Step 5 set out to kill, still leaking here)*
`explain_topic` (`routers/insights.py:90`):
`accuracy = ts.accuracy if ts.accuracy is not None else ts.solved / max(ts.attempted, 1)`.
Since `_do_sync` writes `attempted == solved` and never sets `accuracy` (stays `None`), this is **always 1.0**.
The LLM prompt always claims "100% accuracy" → useless/misleading diagnosis.

Plan (keeps it honest, see Runtime Reality: accuracy is not real data):
- Pass a mastery proxy instead of fake accuracy:
  `mastery = round(1.0 - (ts.weakness_score or 0.0), 2)` (genuinely "how covered, 0..1") and pass it
  where `accuracy` is expected. `volume = ts.solved` unchanged.
- **Rename + reword** `llm.explain_topic_gap(topic, accuracy, volume)` → `(topic, mastery, volume)` and change
  the prompt from "...with {accuracy*100:.0f}% accuracy" to e.g.
  "...has solved {volume} {topic} problems (≈{mastery*100:.0f}% of a target baseline)..." so the prompt no
  longer asserts a false accuracy. Update the cache-key field name to match (`{"mastery": ...}`); 1 call site.

### Fix 4 — `PATCH /questions/{id}/progress` doesn't bust the roadmap cache  *(NEW — found this audit; corrects step5.md)*
`step5.md` claimed `question_progress` only feeds `/insights/recommendations` (LLM-cached) and so `questions.py`
needs no cache-bust. **That analysis missed `/roadmap`:** `routers/roadmap.py` computes per-topic
`user_solved`/`user_attempted` from `question_progress` and caches the whole payload under `roadmap:{uid}` (1h).
So marking a question done won't reflect on the Roadmap page for up to an hour.

Plan:
- `routers/questions.py`: import `delete_cached`; after the commit in `update_progress`,
  `await delete_cached(f"roadmap:{current_user.id}")`.
- Do **not** bust `stats:`/`readiness:` here — `question_progress` genuinely does not feed those (they read
  `topic_scores` + `sheet_progress` only). Keeping it scoped avoids dead cache-busts.

## Part B — End-to-end browser verification (live)

Run backend + frontend against real `backend/.env` (Supabase + Redis) with a **dev JWT** for `shnavii11`
to bypass the GitHub OAuth click. Use the `run` / `verify` skills for launch + observation.
- Start `uvicorn` (:8000) + `vite` (:5173); inject dev JWT into the auth store / localStorage.
- Walk every page against live data: Dashboard (weakest topics on top, red bars, `N solved`, readiness narrative),
  Questions, Roadmap, Sheet, Profile **own** + Profile `/profile/<other-user>` (Fix 1).
- Regression for Fix 2: mark a sheet problem done → reload Dashboard → `sheet.done` + readiness update
  **immediately** (no 1h stale window).
- Regression for Fix 4: mark a question done → reload Roadmap → `user_solved` updates immediately.
- Confirm `GET /insights/recommendations` `weak_topics` = highest-weakness topics.
- If the Gemini key quota has reset, exercise the 3 `/insights/*` endpoints against the real provider
  and confirm non-empty `summary`/`recommendations`/`explanation`.

## Verification checklist
- `cd backend && .venv/bin/python -m pytest -q` → green (Python 3.9 — `Optional`/`Dict`, no PEP 604).
- `cd frontend && npm run test` → green; `./node_modules/.bin/tsc --noEmit` clean (note: `npx tsc` pulls a
  bogus package — always use the local binary or `npm run build`).
- Manual E2E walk above passes; the four bugs no longer reproduce.
- Optional low-value tests: `getPublicProfile` URL shape (vitest); a cache-bust unit test if the cache layer
  is refactored to be injectable.
- Append **Step 6** to `progress.md` + `memory.md`; update persistent backlog memory. Commit; **ask before pushing**.

## Critical files
- Frontend: `frontend/src/pages/Profile.tsx`, `frontend/src/api/auth.ts`, (read) `frontend/src/App.tsx`,
  `frontend/src/store/authStore.ts`, `frontend/src/types/index.ts`.
- Backend: `backend/app/routers/sheet.py`, `backend/app/routers/questions.py`, `backend/app/routers/insights.py`,
  `backend/app/services/llm.py`, (read) `backend/app/routers/roadmap.py`, `backend/app/schemas/user.py`.
- Meta: `progress.md`, `memory.md`, persistent memory.

## Backlog (recorded, not done this step)
- Deployment (Vercel + Railway + Supabase).
- Thicken curated sheet 250 → 350–450 problems (only 2 of 16 sheet sources currently resolve problems).
- Live Gemini run once free-tier quota resets (if not already exercised in Part B).
- Optional hardening (low priority, pre-existing): `llm.py` groq branch uses `gemini_api_key` for its auth
  header; `recommend_next_problems` cache key truncates `solved_ids` to the first 20; `@vitest/ui` devDep is
  unused (no `test:ui` script).
