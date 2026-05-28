# AlgoSweeped — Change Log

Append-only. Each entry records a concrete change to the codebase.

---

## 2026-05-26 00:00 — Initial scaffold

- **Scope:** Entire repo (greenfield)
- **Change:** Created directory tree, meta files (CLAUDE.md, progress.md, memory.md, README.md), db/migrations/0001_init.sql, backend/.env.example, backend/requirements.txt
- **Reason:** Day-1 bootstrap per implementation plan

---

## 2026-05-28 — Backend bring-up & first push

- **Scope:** `.gitignore`, `backend/requirements.txt`, meta files, git remote
- **Changes:**
  - `.gitignore`: added `data/*.json` (covers `.lc_checkpoint.json`) and `.claude/settings.local.json`
  - `backend/requirements.txt`: bumped all pins to Python 3.14-compatible versions (fastapi 0.136.3, uvicorn 0.48.0, pydantic 2.13.4, pydantic-settings 2.14.1, sqlalchemy 2.0.50, asyncpg 0.31.0, httpx 0.28.1, python-jose 3.5.0, passlib 1.7.4, redis 7.4.0, python-multipart 0.0.29, aiofiles 25.1.0, google-generativeai 0.8.6, python-dotenv 1.2.2, alembic 1.18.4)
  - First git commit made; pushed to `https://github.com/shnavii11/name_that_folder.git`
- **Reason:** Old pins (fastapi 0.111, asyncpg 0.29, etc.) lacked Python 3.14 wheels; bumped to latest compatible releases.

---

## 2026-05-28 — Frontend envelope unwrap + API shape reconciliation

- **Scope:** `frontend/src/api/{client,stats,questions,sheet}.ts`, `frontend/src/types/index.ts`, `frontend/src/pages/{Dashboard,Sheet}.tsx`, `frontend/src/components/questions/QuestionRow.tsx`, `frontend/src/store/authStore.ts`, `frontend/.env`
- **Changes:**
  - `client.ts`: response interceptor unwraps `{success, data, meta}` → `data` (only when both keys present, so raw `/users/me` passes through).
  - `types/index.ts`: `Question.companies: string[]` and `companies`/`topics`/`number` optional; `StatsMe` rewritten to real `/stats/me` shape; added `PlatformSnapshot`, `ReadinessScore`.
  - `QuestionRow.tsx`: `(companies ?? [])` guard — `/questions/by-topic` and curated rows carry no `companies` (was a hard crash).
  - `Sheet.tsx`: build `Question` from flattened curated row (`id` ← `question_id`); curated rows have no nested `question`.
  - `Dashboard.tsx`: `summarize()` flattens nested snapshot raw_data; readiness via `/stats/:username/readiness` (`.total`), not `data.readiness_score`.
  - `stats/questions/sheet` api: typed `getReadiness`; `getQuestions`→`Question[]`; `updateSheetProgress` sends `status` as query param.
  - persist key `icode-auth`→`algosweeped-auth`; `VITE_GITHUB_CLIENT_ID` filled (inert — frontend uses no `import.meta.env`).
- **Reason:** Backend wraps most responses in an envelope while `api/*.ts` typed the inner shape, so components received the whole envelope; `/questions/by-topic` and `/sheet/curated` also omit/flatten fields the `Question` type assumed. Reconciled against live Supabase responses; `npm run build` type-clean.
