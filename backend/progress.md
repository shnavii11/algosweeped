

## Step 7 (Part 2) — Curated-sheet thickening 250 → 406 (2026-05-30)
**Diagnosed:** only 2 of 16 `sheet_sources` resolved (lc_top_interview_150=150, lc_top_100_liked=100,
both via LC GraphQL). The 14 GitHub-raw loaders all hit dead URLs (404 → JSON parse error). Corpus has
3944 LC slugs to match against, so resolution — not the corpus — was the bottleneck.

**Fixed loaders** (`scripts/aggregate_sheets.py`): replaced the dead URLs with live sources, verified at
100% slug→corpus resolution before running:
- `load_neetcode_master` — one fetch of neetcode-gh `.problemSiteData.json` (450 problems w/ `neetcode150`
  + `blind75` flags) yields **three** feeds: `neetcode_all` (450), `neetcode_150` (150), `blind75` (75).
- `load_seanprashad` — new URL (`leetcode-patterns/.../questions.json`), uses the `slug` field directly (178).
- Kept the two working LC study-plan loaders. Added `_fetch_json` raw-caching to `data/sheets/<id>.json`.
- Sources with no surviving JSON feed (Striver, Grind, CSES, AlgoExpert, USACO, A2OJ, NeetCode-250, Babbar)
  intentionally NOT forced — they stay as 0-count `sheet_sources` rows (genuine misses, per plan).

**Re-aggregated → Supabase:** 1103 `sheet_source_problems` across 6 resolving sources; optimal mix =
**406 problems** (was 250), 0 dangling question_ids, difficulty 98E/239M/69H, per-topic now 8–28 (previously
many topics stuck at 8). Bumped `curated_sheet.generator_version` 1.0 → 1.1. Busted `sheet:curated` Redis key.

**Next:** Part 3 (live E2E browser walk), Part 4 (cleanup: README/requirements/minor hardening) — not yet done.


## Step 9 — Sidebar overall progress bar (platforms + sheet blend) (2026-06-01)
**Frontend-only, no backend change** (per step9.md). Added an at-a-glance "Overall Progress" bar to the
left sidebar, visible on every page, blending platform problem-solving with curated-sheet completion.

- **New `frontend/src/components/ui/OverallProgress.tsx`:** exported pure helper
  `computeOverall(dsaConsistency, sheetPct) = clamp(round((dsa + pct)/2), 0, 100)` — 50/50 blend.
  Platforms half = `readiness.breakdown.dsa_consistency` (LC+CF, already 0–100, one source of truth).
  Sheet half = `/sheet/progress/me.pct` (done/406) — NOT the readiness `sheet_progress` breakdown.
  Three `useQuery`s reuse the SAME query keys as Dashboard/Sheet (`['readiness', username]`, `['stats']`,
  `['sheet-progress']`) so React Query serves them from cache. LC/CF subtext counts extracted via the
  same field paths as `Dashboard.tsx:summarize`. Bar styling mirrors `TopicAccordion`. Graceful loading
  (em-dash + 0% bar) until readiness + sheet-progress resolve.
- **`Layout.tsx`:** mounted `<OverallProgress />` in a `border-t border-gray-800 p-4` block between
  `<nav>` and the Sign-out footer.
- **`Sheet.tsx`:** sheet-progress mutation `onSuccess` now also invalidates `['readiness']` + `['stats']`
  (Step-7 Fix 2 already busts those Redis keys server-side) so the sidebar bar ticks up after marking
  problems done.
- **Tests:** new `OverallProgress.test.ts` (2 vitest, pure helper) → frontend 7 passing; `tsc --noEmit`
  clean; backend still 21 passing (unaffected).

### Step 9 follow-up — sidebar bottom block was off-screen (layout fix)
**Symptom:** after mounting `<OverallProgress />` between the nav and the Sign-out footer, neither the
new bar NOR the pre-existing "Sign out" button was visible — both sat below the fold.
**Root cause:** `Layout.tsx` root was `flex min-h-screen` while `<main>` had `overflow-auto`. With
`min-h-screen` the container grows to content height, so `main`'s `overflow-auto` never engages and the
whole page scrolls — pushing the sidebar's bottom blocks off-screen. Pre-existing latent bug; Step 9 just
made it visible by adding content there.
**Fix:** one line — `min-h-screen` → `h-screen`. Now `main` scrolls internally and the sidebar (with the
Overall Progress bar + Sign out) is pinned in the viewport on every page.
**Verified via headless-Chromium DOM read** (CDP, authed as shnavii11): `rootClass="flex h-screen"`,
sidebar renders `Overall Progress 26%` · `LC 213 · CF 6 · Sheet 0/406` · `Sign out`. The user's earlier
"no change" was a stale Safari module cache, not a code issue (server served the correct bundle, `no-cache`
headers). `tsc --noEmit` clean.
