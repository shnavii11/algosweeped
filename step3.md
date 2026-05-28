# Step 3 — Intelligence-layer correctness + curated-sheet tracking

## Context

Step 2 brought the frontend up and reconciled the API layer against the live backend (response-envelope
unwrap + shape fixes), pushed as commit `77e9231`. During verification, two real bugs surfaced that make
the app's headline analytics wrong, plus a leftover dev process. This step fixes the **first** of the
three directions the user wants (1 → 2 → 3, step by step); options 2 and 3 are recorded as backlog.

Step 3 = **option 1 (fix analytics + sheet tracking)**, done first because the LLM (option 2) consumes
`weak_topics` and would run on garbage until Bug 1 is fixed.

Intended outcome: weakness analysis, readiness, and roadmap progress reflect the canonical 22 topics; the
curated-sheet tracker loads and persists progress end-to-end. Keep the change surface tight — touch only
what these fixes require.

## Bug audit (found during Step 2 verification)

| # | Bug | Evidence |
|---|---|---|
| 1 | **Sync stores raw LeetCode tag-slugs, not canonical topics.** `backend/app/routers/stats.py:~116` writes `topic = tag_data.get("tagSlug")` verbatim. `scripts/lib/lc_topic_map.json` exists but only the scraper uses it. | `/stats/me` `topic_scores` topics are `array`, `binary-tree`, `data-stream`, `brainteaser`… `/roadmap` `weakness_score` is `None` for arrays/strings/hashing/prefix-sum (non-null only where a raw slug coincidentally equals canonical, e.g. `binary-search`, `dynamic-programming`). `TOPIC_WEIGHTS` (keyed canonical) never apply. |
| 2 | **Readiness `topic_coverage` undercounts** — a direct consequence of #1: `CORE_TOPICS` (`arrays`/`strings`/`graphs`) never match raw `array`/`string`/`graph`. | `/stats/shnavii11/readiness` `topic_coverage` = 33.3 despite a broad solve history. |
| 3 | **Curated-sheet progress is non-functional.** In `frontend/src/pages/Sheet.tsx`, `progress` is never hydrated (`getMySheetProgress` unused) and never updated (`setProgress` unused); the toggle inside `QuestionRow` always writes `/questions/:id/progress` (question table), not `/sheet/progress/:id`. | Sheet header "X solved" + bars stay 0; `/stats/me` `sheet` block and readiness `sheet_progress` stay empty. |
| — | **Leftover:** duplicate vite on `:5174` (PID 27156); `:5173` is canonical. | `lsof -ti:5174` |

Step 2 edits themselves verified clean (Dashboard/Sheet coherent, build type-clean, envelope + shape
reconciliation correct against live data).

## Execution steps

### Step 0 — kill the duplicate vite
`lsof -ti:5174 | xargs kill` (only :5174 / PID 27156; leave :5173 and the :8000 backend running).

### A. Backend — normalize LC tag-slugs → canonical topics
1. `backend/app/services/intelligence.py`: add a `LC_TAG_TO_TOPIC` dict (inline mirror of
   `scripts/lib/lc_topic_map.json` — keeps the backend self-contained for deploy) + a
   `normalize_lc_topic(raw) -> str | None` helper. Reuse existing `compute_weakness_score` (already keyed
   on canonical `TOPIC_WEIGHTS`).
2. `backend/app/routers/stats.py` (`_do_sync` topic-score recompute block):
   - Aggregate `problemsSolved` by **canonical** topic — for each raw tag `canon = normalize_lc_topic(raw)`;
     skip `None`; `agg[canon] += problemsSolved`.
   - `DELETE FROM topic_scores WHERE user_id = :uid` once, then insert one fresh row per canonical topic
     (`solved`, `attempted=solved`, `weakness_score=compute_weakness_score(canon, solved, solved)`). The
     delete clears stale raw-slug rows so canonical and legacy rows don't coexist.
   - `compute_readiness_score` needs **no** change — it already checks `ts["topic"] in CORE_TOPICS` and
     starts matching once topics are canonical.

### B. Frontend — wire curated-sheet progress
3. `frontend/src/api/sheet.ts`: type `getMySheetProgress` → unwrapped `{ progress_map, done, total, pct }`.
   (`updateSheetProgress` already sends `status` as a query param from Step 2.)
4. `frontend/src/types/index.ts`: add `SheetProgressMe { progress_map: Record<string,'todo'|'attempted'|'done'>; done: number; total: number; pct: number }`.
5. `frontend/src/components/questions/QuestionRow.tsx`: when an `onStatusChange` prop is provided,
   delegate persistence to the parent and skip the internal `updateQuestionProgress` call; with no
   `onStatusChange` (Questions page) keep current behavior.
6. `frontend/src/components/questions/TopicAccordion.tsx`: accept + forward an optional `onStatusChange`
   to each `QuestionRow`.
7. `frontend/src/pages/Sheet.tsx`: `useQuery(['sheet-progress'], getMySheetProgress)` to hydrate; keep a
   local `overrides` map for optimism; `progress = { ...progress_map, ...overrides }`; a `useMutation`
   calling `updateSheetProgress(id, status)`; pass `onStatusChange` down through `TopicAccordion`. Drive
   the header "done" count + bars off `progress`. Removes the dead `setProgress`.

`problem_id` in `sheet_progress` is the `question_id` used as `Question.id`, so the maps line up; `/stats/me`
`sheet` block and readiness `sheet_progress` populate once writes land.

### C. Meta
8. Append a Step 3 entry to `progress.md` and `memory.md` (what changed, results), plus the **Backlog**
   below.
9. Record the roadmap sequencing in persistent memory so future sessions resume correctly.
10. Commit; **ask before pushing** to `origin` (matches Step 2).

## Verification

- **Backend:** `POST /stats/sync` (dev JWT, user `shnavii11`); then `GET /stats/me` → `topic_scores` topics
  are canonical (`arrays`, `trees`, `graphs`…), no raw slugs; `GET /roadmap` → `weakness_score` populated
  for canonical topics (no longer `None` for arrays/strings); `GET /stats/shnavii11/readiness` →
  `topic_coverage` rises to a sensible value.
- **Frontend:** `npm run build` type-clean. On the Sheet page, toggling a problem persists (re-fetch
  `getMySheetProgress` shows it; `/stats/me` `sheet.done` increments; header count + bars update). Questions
  page toggle still writes `question_progress` (unchanged).
- Browser/visual walk-through is user-driven (noted, not run headlessly).

## Critical files (no others)

- Backend: `backend/app/services/intelligence.py`, `backend/app/routers/stats.py`.
- Frontend: `frontend/src/api/sheet.ts`, `frontend/src/types/index.ts`,
  `frontend/src/components/questions/QuestionRow.tsx`,
  `frontend/src/components/questions/TopicAccordion.tsx`, `frontend/src/pages/Sheet.tsx`.
- Meta: `step3.md` (this file), `progress.md`, `memory.md`, persistent memory.

## Backlog / next phases (agreed order)

1. **(this step) Option 1 — fix analytics + sheet tracking.** ← Step 3
2. **(next) Option 2 — wire the Gemini LLM.** Hook `recommend_next_problems` / `summarize_readiness` /
   `explain_topic_gap` (`backend/app/services/llm.py`) into endpoints + the Dashboard UI. Now fed correct
   `weak_topics` because Step 3 fixed topic normalization. Needs `GEMINI_API_KEY` (already set). Cache each
   call in Redis by `sha256(inputs)` (24h) per the LLM contract.
3. **(after) Option 3 — thicken the curated sheet** 250 → 350–450 via the sheet loaders / aggregation
   (`scripts/aggregate_sheets.py`, `scripts/lib/sheet_loaders/`); only 2 of 16 sources currently resolve
   problems.

## Known gaps (unchanged, deferred)

- Sheet-page toggle persists to `sheet_progress` after this step; the Questions-page toggle still uses
  `question_progress` (intended — separate trackers).
- LLM (Gemini), Redis (Upstash, optional), and deployment (Vercel + Railway) unchanged.
- `compute_weakness_score` is called with `attempted = solved`, so its accuracy term is always 1.0 and the
  score is effectively a weighted volume metric — acceptable for now; revisit if richer accuracy data
  becomes available.
