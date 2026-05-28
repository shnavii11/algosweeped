# Step 2 — Frontend bring-up, OAuth, envelope fix & live sync

## Context

Steps 0–4 are done and pushed to `github.com/shnavii11/algosweeped`: schema (14 tables), corpus
(15,160 questions / 36,362 topic links / 10,016 company tags), 22 roadmap topics, a thin curated
sheet (250), and a FastAPI backend whose read endpoints are all verified against live Supabase.

The genuine next link in the chain (implementation plan ordering `schema → scraper → backend →
frontend`) is the **frontend**. `node_modules` is present and Vite boots, but the app has never been
verified against the running backend. This phase brings the frontend up end-to-end with **real
GitHub OAuth**, fixes a contract bug found during exploration, and runs a **real platform sync** so
the Dashboard shows live data.

## Current-state analysis

| Layer | State |
|---|---|
| Schema / corpus / roadmap (steps 0–3) | **Done** (counts above). |
| Curated sheet (step 2 data) | **Thin** — 250 vs 350–450 target. Deferred. |
| Backend (step 4) | **Booted & verified** — all read endpoints return live Supabase data. |
| Frontend (step 5) | **Boots, never verified against backend.** This step. |
| Repo | Renamed to **AlgoSweeped**, pushed to `github.com/shnavii11/algosweeped`. |

Exploration findings that shape this step:

- **Frontend wiring:** `client.ts` uses `baseURL:'/api'`; `vite.config.ts` proxies `/api` →
  `localhost:8000` (strips `/api`). Auth is JWT-in-localStorage (`authStore`, persist key
  `icode-auth`). Everything except `/login` is gated by `RequireAuth`. `Login.tsx` starts OAuth via
  `/api/auth/github` and reads `?token=` on return.
- **`VITE_*` env vars are inert.** Grep shows **no `import.meta.env` usage** and **no supabase-js** in
  the frontend — all data flows through the backend JWT API via the proxy. So `VITE_API_URL`,
  `VITE_GITHUB_CLIENT_ID`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` are scaffolding; we create
  `frontend/.env` for completeness but it won't change runtime behavior today.
- **Core bug — response-envelope mismatch.** Backend wraps most responses in `{success, data, meta}`,
  but every `api/*.ts` call does `.then(r => r.data)` and types it as the *inner* shape — so components
  receive the whole envelope, not the payload. Affects `stats.ts`, `questions.ts` (also mis-typed as
  `{items,total}`), `sheet.ts`, `roadmap.ts`. **Exception:** `/users/me` returns a raw object (no
  envelope) and is handled correctly — so a blanket unwrap must not break it.
- **OAuth flow:** `GET /auth/github` → GitHub authorize → `GET /auth/github/callback` upserts the user,
  mints a JWT, redirects to `{FRONTEND_URL}/login?token=...&new=...`. Needs `GITHUB_CLIENT_SECRET`, the
  OAuth app's callback set to `localhost:8000/auth/github/callback`, and `FRONTEND_URL` matching the
  real frontend port.
- **Port clash:** a stale process holds 5173, so Vite fell back to 5174. Backend CORS allows both, but
  the OAuth redirect targets `FRONTEND_URL` — these must agree.
- **Dashboard data:** the lone user has no `platform_snapshots`/`topic_scores` yet (sync never ran), so
  Dashboard/Profile render empty until a sync runs. `POST /stats/sync` exercises
  `services/{leetcode,codeforces,github}.py` for the first time — expect fixes.

## Decisions (confirmed with user)

- **Auth:** wire **full GitHub OAuth** end-to-end (not just a dev-token bypass).
- **Scope:** do **both** — (1) boot + render + envelope fix, **and** (2) live platform sync so the
  Dashboard shows real LeetCode/Codeforces/GitHub data.

## Prerequisites (needed from user)

- `GITHUB_CLIENT_SECRET` in `backend/.env` (CLIENT_ID `Ov23lia1SiYsq91W6imI` already set).
- GitHub OAuth app **Authorization callback URL** = `http://localhost:8000/auth/github/callback`.
- `GITHUB_TOKEN` (read-only scope) in `backend/.env` for the GitHub fetcher during sync.
- LeetCode / Codeforces / GitHub handles to onboard with.

## Execution steps

### A. Frontend boot & config
1. Create `frontend/.env` with the four `VITE_*` vars (VITE_API_URL filled; others as available).
2. Free the stale process on 5173 (`lsof -ti:5173 | xargs kill`) so Vite uses the canonical 5173 that
   `FRONTEND_URL`/CORS expect (or set `FRONTEND_URL=http://localhost:5174` — prefer freeing 5173).
3. `npm run dev`; confirm Login renders.

### B. Fix the envelope mismatch (core code change)
4. In `client.ts`, add a **response interceptor** that unwraps `{success, data}` → `data` when `success`
   is present, leaving non-enveloped responses (`/users/me`) untouched. Single-point fix.
5. Reconcile shapes the interceptor alone doesn't settle — read `questions.py` router + `Questions.tsx`
   and align `api/questions.ts` (list is an enveloped array; `total` likely lives in `meta`, not
   `{items,total}`). Confirm `getQuestionsByTopic` / `getCuratedSheet` / `getSheetSources` /
   `getRoadmap` yield correct post-unwrap shapes.
6. `npm run build` (tsc) to catch type fallout.

### C. Full GitHub OAuth
7. Set `GITHUB_CLIENT_SECRET`, `FRONTEND_URL`, `GITHUB_TOKEN` in `backend/.env`; confirm OAuth app
   callback URL. Restart backend.
8. Click "Continue with GitHub" → authorize → callback → token in URL → app stores it → routes to
   `/onboarding` (new) or `/dashboard`. Verify persistence + 401-logout.
9. Minor polish (optional): rename persist key `icode-auth` → `algosweeped-auth`.
   - Contingency: if OAuth config stalls, mint a dev JWT and load `/login?token=...` to unblock UI
     verification of corpus pages (B/E) while OAuth is sorted.

### D. Live sync + dashboard data
10. Onboarding sets `lc_username`/`cf_handle`/`gh_username` via `PATCH /users/me` (verify `Onboarding.tsx`).
11. `POST /stats/sync` → background task runs the three platform fetchers → snapshots + topic_scores.
    First real run of `services/{leetcode,codeforces,github}.py` + `intelligence.py` — fix breakage
    (LC GraphQL `Referer`, GitHub `Bearer` token, CF handle shape) as surfaced.
12. Verify Dashboard (platform cards, topic table, readiness) + Profile show real data.

### E. End-to-end page verification (browser, golden path)
Login → Onboarding → Dashboard → Questions (filter/search/pagination) → Roadmap (22 topics) →
Sheet (250 problems; toggle progress persists) → Profile.

### F. Meta + commit
13. Append entries to `progress.md` and `memory.md`.
14. Commit and push to `origin` (algosweeped).

## Critical files

- `frontend/.env` (create) — VITE_* (note: currently inert).
- `frontend/src/api/client.ts` — **envelope-unwrap interceptor (core fix)**.
- `frontend/src/api/{questions,sheet,roadmap,stats}.ts` — shape reconciliation.
- `frontend/src/pages/{Onboarding,Dashboard,Questions,Sheet,Roadmap,Profile}.tsx` — verify/adjust.
- `backend/.env` — `GITHUB_CLIENT_SECRET`, `FRONTEND_URL`, `GITHUB_TOKEN`.
- `backend/app/services/{leetcode,codeforces,github}.py`, `intelligence.py` — sync path.
- `progress.md`, `memory.md` — meta.

## Verification

- Vite serves; Login renders; OAuth round-trip succeeds and lands on dashboard/onboarding.
- `npm run build` is type-clean.
- Corpus pages show live data: Questions (filters work), Roadmap (22 topics), Sheet (250 problems,
  progress toggle persists via `PATCH /sheet/progress/:id`).
- After sync, Dashboard + Profile show real LeetCode/Codeforces/GitHub numbers.
- `git log --oneline` shows the new commit; pushed to the algosweeped remote.

## Known gaps (flagged, deferred)

1. Curated sheet thin (250 vs 350–450) — sheet loaders resolved only 250 source entries.
2. LLM service (Gemini) not yet exercised (`recommend`/`summarize`/`explain`); needs `GEMINI_API_KEY`.
3. Redis (Upstash) optional — `cache.py` degrades gracefully if absent.
4. Deployment (Vercel + Railway) — a later step.
