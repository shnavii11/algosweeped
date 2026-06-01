

## 2026-05-30 — Step 7 Part 2: curated sheet 250→406
- Root cause of "only 2/16 sources resolve": the 14 GitHub-raw loader URLs in aggregate_sheets.py were
  all dead (404). Corpus (3944 LC slugs) was fine.
- Live sources found (100% slug→corpus match): neetcode-gh `.problemSiteData.json` (450, flags
  neetcode150/blind75 → 3 feeds) and seanprashad `src/data/questions.json` (178, has `slug`). Grind75 &
  Striver repos are dead — left as genuine 0-count misses.
- aggregate_sheets.py: new `load_neetcode_master` + `_fetch_json` raw-cache; rewrote `load_seanprashad`;
  `load_all_sheets` now returns flat batches from live sources only; generator_version 1.0→1.1.
- Result: 6 sources resolve (was 2), curated mix 406 (was 250), 0 dangling, 98E/239M/69H. Busted
  `sheet:curated` Redis key. No .env touched.


## 2026-06-01 — Step 9: sidebar Overall Progress bar (frontend-only)
- New `components/ui/OverallProgress.tsx` + exported `computeOverall(dsa, pct)=clamp(round((dsa+pct)/2),0,100)`.
  50/50 blend: platforms = `readiness.breakdown.dsa_consistency` (0–100); sheet = `/sheet/progress/me.pct`
  (done/406, NOT the readiness sheet_progress breakdown). Reuses existing query keys (`['readiness',username]`,
  `['stats']`, `['sheet-progress']`) → served from React Query cache.
- Mounted in `Layout.tsx` between nav and Sign-out footer. `Sheet.tsx` mutation now also invalidates
  `['readiness']`+`['stats']` so the bar refreshes after marking sheet problems done.
- New `OverallProgress.test.ts` (pure helper). FE 7 tests pass, tsc clean, BE 21 still pass. No backend change.
- Follow-up fix: `Layout.tsx` root `min-h-screen`→`h-screen` (one line). Latent bug — with `min-h-screen`
  the container grew to content height so `<main>`'s `overflow-auto` never engaged; the whole page scrolled
  and the sidebar's bottom blocks (Overall Progress bar + Sign out) fell off-screen. `h-screen` makes `main`
  scroll internally and pins the sidebar. Verified via headless-Chromium CDP DOM read (authed): sidebar shows
  `Overall Progress 26% · LC 213 · CF 6 · Sheet 0/406 · Sign out`. The "no change" the user saw was a stale
  Safari module cache, not code (server served correct bundle w/ `no-cache`).
