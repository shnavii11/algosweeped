# Step 1 — Backend bring-up & verification + first commit/push

## Context

The project was assumed to be "just step 0a/0b." A codebase audit (2026-05-28) shows otherwise —
the **data layer (implementation plan steps 0–3) is essentially complete**, but the meta files never
recorded it and nothing has ever been committed.

Verified current state:

| Layer | State |
|---|---|
| Supabase schema (step 0) | **Done** — all 14 tables exist |
| Corpus fetch (step 1) | **Done** — 15,160 questions (3,944 LC via `rest_all`, 11,216 CF via `official_api`), 36,362 topic links, 10,016 company tags. `fetch_runs` has 5 `ok` rows. |
| Sheets + curated mix (step 2) | **Partial** — 16 `sheet_sources`, but only 250 `sheet_source_problems` resolved → curated sheet = 250 problems (target was 350–450). Top topics hit the 28-quota (arrays/strings=28); long tail is thin. **Deferred.** |
| Roadmap (step 3) | **Done** — 22 `roadmap_topics`. |
| Backend (step 4) | **Written, never booted.** Routers/services/models are real implementations, but the `.venv` only has scraper deps (asyncpg, httpx, bs4, dotenv). FastAPI/uvicorn/sqlalchemy/redis/pydantic/google-generativeai are **not installed**. |
| Frontend (step 5) | Written; `node_modules` present (154 pkgs). Unverified — **next step after this one.** |
| Meta files | **Stale** — `progress.md`/`memory.md` only record the 2026-05-26 scaffold. |
| Git | **Zero commits, no remote configured.** |

**This step** (scope = *backend bring-up only*): update the meta files to reflect reality, get the
FastAPI backend running against the live Supabase, smoke-test the read endpoints that serve the
populated corpus, then make the first commit and push to
`https://github.com/shnavii11/name_that_folder.git`.

The implementation plan's own ordering is `schema → scraper → backend → frontend`; backend
verification is the genuine next link in that chain.

## Key facts that shape execution

- **Python 3.14.3** in `.venv`. `requirements.txt` pins are old (fastapi 0.111, pydantic 2.7.1,
  asyncpg 0.29, google-generativeai 0.7.2). These likely lack 3.14 wheels. The venv already proves
  `asyncpg 0.31` + `httpx 0.28` work on 3.14 → **expect to bump pins**. Main risk of this step.
- `backend/app/config.py` loads `.env` from **CWD** → the server **must be started from `backend/`**.
- `backend/app/cache.py` degrades gracefully when Redis is unreachable (swallows exceptions) →
  endpoints won't break if Upstash is down.
- **Public (no-auth) read endpoints** to smoke-test: `/health`, `/questions`, `/questions/by-topic`,
  `/sheet/curated`, `/sheet/sources`.
- **Auth-gated** (need a JWT): `GET /roadmap`, `GET /sheet/progress/me`, `PATCH .../progress`.
  There is 1 user row in the DB.
- `.gitignore` correctly excludes `backend/.env`, `frontend/.env`, `.venv/`, `node_modules/`,
  `data/snapshots/`, `data/sheets/`. **Gaps:** `data/.lc_checkpoint.json` (12 MB) and
  `.claude/settings.local.json` are NOT ignored and would get committed.

## Execution steps

### 1. Fix `.gitignore`
Add `data/.lc_checkpoint.json` (or `data/*.json`) and `.claude/settings.local.json`. Confirm with
`git add -A -n` that no file >500 KB and no secret/env file is staged.

### 2. Install backend deps
- `source .venv/bin/activate`, then `pip install -r backend/requirements.txt`.
- If old pins fail to build on Python 3.14: bump the failing packages to their latest 3.14-compatible
  releases (fastapi, pydantic/pydantic-settings, sqlalchemy, asyncpg→0.31, google-generativeai, etc.)
  and **update `backend/requirements.txt`** to the versions that actually install.
- Fallback if 3.14 proves intractable: create a Python 3.11 venv (CLAUDE.md's stated runtime) and
  install there. Prefer the 3.14 path first to avoid environment churn.
- Confirm: `cd backend && python -c "import app.main; print(len(app.main.app.routes))"`.

### 3. Boot the server
`cd backend && uvicorn app.main:app --port 8000` (background). Confirm startup logs are clean and
the async SQLAlchemy engine binds to the Supabase `DATABASE_URL`.

### 4. Smoke-test read endpoints (see Verification)
Curl each public endpoint; confirm live Supabase data flows through. For auth-gated endpoints, mint a
short-lived JWT for the existing user with the repo's `jwt_secret` (matching `deps.get_current_user`'s
decode) and verify `GET /roadmap` returns the 22 ordered topics. If JWT minting is fiddly, verify the
auth-gated routes via `/docs` manually or **defer them to the frontend-auth step** and note it.

### 5. Fix any breakage
Address import errors, SQL/model mismatches, or driver issues surfaced by steps 2–4. Keep fixes
minimal and within backend scope.

### 6. Update meta files (reflect true state + this step's outcome)
- **`progress.md`** — append an entry correcting the record: data layer (steps 0–3) complete with the
  counts above; backend booted & verified; endpoints confirmed; flag the thin curated sheet
  (250 vs 350–450) and unverified frontend as `Next`.
- **`memory.md`** — append a factual change-log entry (deps installed / requirements bumped,
  `.gitignore` fix, any backend fixes).
- **`CLAUDE.md`** — only correct anything proven wrong (e.g. `LEETCODE_CSRF_TOKEN` is the real env
  name vs the plan's `CSRF_TOKEN`; note CF was fetched metadata-only). Keep edits surgical.

### 7. First commit + push
- `git remote add origin https://github.com/shnavii11/name_that_folder.git`.
- Stage with explicit paths (not blanket `-A`) after re-confirming no `.env`/large files; commit the
  ~92 tracked files as the initial commit.
- `git push -u origin main`. (Will prompt for the user's GitHub auth — surface that if it blocks.)

## Critical files

- `backend/requirements.txt` — likely bumped for Python 3.14 (the substantive code change).
- `.gitignore` — add checkpoint + local settings.
- `progress.md`, `memory.md`, `CLAUDE.md` — meta updates.
- Read-only references: `backend/app/{main,config,database,cache}.py`,
  `backend/app/routers/{questions,roadmap,sheet,deps}.py`.

## Verification

Backend is "up and correct" when, with the server running on `:8000`:

```
curl -s localhost:8000/health                            # {"status":"ok","version":"1.0.0"}
curl -s "localhost:8000/questions?topic=arrays&limit=5"  # success:true, 5 rows w/ topics[]+companies[]
curl -s localhost:8000/questions/by-topic                # success:true, ~22 topic keys
curl -s localhost:8000/sheet/curated                     # success:true, ~250 problems grouped by topic
curl -s localhost:8000/sheet/sources                     # success:true, 16 sources
# auth-gated (with minted JWT) OR via /docs:
curl -s localhost:8000/roadmap -H "Authorization: Bearer <jwt>"  # 22 ordered topics
```

All read endpoints return live Supabase rows (counts match the table audit). Then the meta files are
updated and the initial commit is pushed to the remote, verifiable with `git log --oneline` and the
GitHub repo showing the push.

## Known gaps (flagged, NOT in this step's scope)

1. **Curated sheet is thin** — 250 problems vs 350–450 target; sheet loaders resolved only 250
   source entries. Deferred; recorded in `progress.md`.
2. **Frontend unverified** — the natural step after this one (`node_modules` already present).
3. **`GET /roadmap` requires auth** — public-ish data behind a JWT; revisit when wiring frontend auth.
