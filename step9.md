# Step 9 — Sidebar overall progress bar (platforms + sheet blend)

> Numbering convention (CLAUDE.md): `stepN.md`'s N = the `progress.md` "Step N" it becomes.
> Continues from **Step 8** (Questions progress + Dashboard GitHub card, commit `2850764`). This is
> the next build step and will be logged as **Step 9**. Step 8's record is untouched.

## Context

The left sidebar (`frontend/src/components/ui/Layout.tsx`) currently shows the brand, the nav rows
(Dashboard / Questions / Roadmap / Sheet / Profile), and a "Sign out" footer — but no at-a-glance
sense of how far along the user is. Add an **overall progress bar in the sidebar, near the nav
rows**, that blends **problem-solving across platforms (LeetCode + Codeforces)** with **curated-sheet
completion**. GitHub and topic-coverage are intentionally excluded (chosen metric: "Platforms +
Sheet blend").

**Key finding — everything needed is already exposed; this is frontend-only.** No backend change.
- `GET /stats/:username/readiness` (`api/stats.ts:getReadiness`) returns `breakdown.dsa_consistency`
  — a **0–100** score that already averages LeetCode and Codeforces using the existing targets in
  `backend/app/services/intelligence.py:compute_readiness_score`
  (`lc_dsa = min((E·1+M·2+H·3)/300,1)`, `cf_dsa = min(cf_solved/200,1)`, `dsa = (lc_dsa+cf_dsa)/2`).
  Reusing this avoids inventing new platform denominators and keeps one source of truth.
- `GET /sheet/progress/me` (`api/sheet.ts:getMySheetProgress`, type `SheetProgressMe`) returns
  `done`, `total` (= curated sheet size, 406, from `curated_sheet_problems`), and `pct`.
  > Do **not** use the readiness `sheet_progress` breakdown for the sheet half — it divides by rows
  > the user has touched, not 406. `/sheet/progress/me.pct` is the correct done/406 value.
- `GET /stats/me` (`api/stats.ts:getMyStats`, type `StatsMe`) carries the raw LeetCode/Codeforces
  snapshots for the subtext counts (same extraction the Dashboard's `summarize()` already does:
  LC solved = `submitStatsGlobal.acSubmissionNum` All count; CF solved = `problemsSolved`).

All three queries are **already fetched elsewhere** (Dashboard uses stats + readiness; Sheet page
uses sheet progress), so React Query serves them from cache when navigating — cheap in the sidebar.

Outcome: a labelled progress bar in the sidebar, visible on every page, showing one overall % with a
small `LC {n} · CF {n} · Sheet {done}/{total}` subtext.

## Formula (state it in code as a comment)

```
overall = round( (readiness.breakdown.dsa_consistency + sheetProgress.pct) / 2 )
```
- Platforms half = `dsa_consistency` (LC+CF, already 0–100). Sheet half = `sheetProgress.pct` (done/406).
- Equal 50/50 weight — simple, defensible, easy to tweak later. Clamp to `[0,100]`.

## Implementation (frontend only)

### 1. New component — `frontend/src/components/ui/OverallProgress.tsx`
- Read `username` from `useAuthStore` (mirror `Layout.tsx:15`).
- Three `useQuery`s reusing existing api fns: `getReadiness(username)` (enabled when username set),
  `getMySheetProgress()`, `getMyStats()`.
- Compute `overall` per the formula; derive LC/CF solved for subtext from the stats snapshots
  (reuse the same field paths as `Dashboard.tsx:summarize`).
- Render: a small label ("Overall Progress"), the big `{overall}%`, a Tailwind track+fill bar
  (mirror the bar styling already in `components/questions/TopicAccordion.tsx:30-38` —
  `h-1.5 rounded-full bg-gray-800` track, `bg-blue-500` fill, `width: {overall}%`), and a muted
  subtext line `LC {lc} · CF {cf} · Sheet {done}/{total}`.
- Graceful states: while data loads, show the bar at 0% / skeleton dashes; if a query errors, still
  render what's available (don't crash the whole sidebar).

### 2. Mount it in the sidebar — `frontend/src/components/ui/Layout.tsx`
- Import and render `<OverallProgress />` inside the `<aside>`, in a bordered block **between the
  `<nav>` (flex-1) and the "Sign out" footer** so it sits with the nav rows and stays pinned above
  the footer. (Add `border-t border-gray-800 p-4` to match the existing footer block styling.)
- No change to nav items or routing.

> Reuse, don't reinvent: bar styling from `TopicAccordion`, border styling from the existing sidebar
> footer, query fns from `api/stats.ts` + `api/sheet.ts`, types `ReadinessScore` / `SheetProgressMe`
> / `StatsMe` from `types/index.ts` (no type changes needed).

## Out of scope
- No backend changes, no new endpoints, no `.env`/config edits.
- No change to the readiness formula itself or the Dashboard.

## Tests
- `cd frontend && npm run test` → existing 5 vitest still green.
- `cd frontend && ./node_modules/.bin/tsc --noEmit` → clean (NOT `npx tsc`).
- Backend unaffected (no backend change) but run `cd backend && .venv/bin/python -m pytest -q` once
  to confirm still 21 green.
- Optional: a tiny vitest asserting `overall = round((dsa + pct)/2)` for sample inputs (pure helper
  if the math is extracted to a function).

## Verification (end-to-end)
Backend on :8000 + frontend on :5173.
1. Log in (dev JWT for `shnavii11`); the sidebar shows **Overall Progress** with a filled bar +
   `LC … · CF … · Sheet …/406` subtext on every page.
2. Cross-check the number is sane: it should sit between the Dashboard's readiness and the sheet %
   (it's the average of the platform sub-score and the sheet %).
3. Go to the **Sheet** page, mark a few problems done → return to any page; the sidebar bar ticks up
   (Step-7 Fix 2 busts `stats:`+`readiness:` on a sheet write; ensure the React Query keys for
   `readiness` / sheet-progress are invalidated/refetched so the sidebar reflects it — invalidate
   `['readiness', username]` + the sheet-progress query in the Sheet page's mutation if not already).

## Critical files
- New: `frontend/src/components/ui/OverallProgress.tsx`.
- Edit: `frontend/src/components/ui/Layout.tsx` (mount the component).
- Reuse (read-only): `api/stats.ts`, `api/sheet.ts`, `pages/Dashboard.tsx` (summarize field paths),
  `components/questions/TopicAccordion.tsx` (bar styling), `types/index.ts`.

## Logging (CLAUDE.md convention)
- After build: append a **Step 9** entry to `progress.md` + a change entry to `memory.md`; tick the
  item in `remaining.md`. Commit; **ask before pushing.**
