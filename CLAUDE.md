# AlgoSweeped — Project Reference

> **EVERY PROMPT working on this project MUST read this file first.**
> Use it as the single source of truth. Do not re-derive information that lives here.
> This saves tokens and keeps all decisions consistent across sessions.
> After reading, log changes to `memory.md` and steps to `progress.md`.

---

## Project Summary

**AlgoSweeped** is a developer progress dashboard for CS students preparing for tech internships.
It aggregates data from LeetCode, Codeforces, and GitHub into one place, shows topic-wise weakness analysis, computes an interview readiness score, exposes a public profile, and provides a curated DSA sheet tracker built from 15+ well-known online sheets.

---

## Tech Stack

| Layer | Tech | Note |
|---|---|---|
| Frontend | React 18 + TypeScript + Tailwind CSS | Vite, React Query v5, Recharts, Zustand |
| Backend | FastAPI + Uvicorn + Python 3.11 | async throughout |
| Database | **Postgres via Supabase only** | No SQLite, no local DB, ever |
| Cache | Redis via Upstash | free tier |
| Auth | JWT + GitHub OAuth via Supabase Auth | |
| LLM | Gemini 2.0 Flash (Google AI Studio free tier) | pluggable via env var |
| Deployment | Vercel (frontend) + Railway (backend) + Supabase (DB) | |

---

## Repository Layout

```
icode-plus/
├── CLAUDE.md          ← this file
├── progress.md        ← step log (append-only)
├── memory.md          ← change log (append-only)
├── README.md
├── db/
│   ├── migrations/
│   │   └── 0001_init.sql       ← full schema, run once in Supabase SQL editor
│   └── seed.sql
├── data/              ← snapshots/exports only, NOT source of truth
│   ├── snapshots/
│   ├── sheets/        ← raw downloads of external DSA sheets
│   └── _fetched_at.json
├── scripts/           ← one-shot scrapers, write directly to Supabase
│   ├── fetch_all.py
│   ├── fetch_leetcode.py
│   ├── fetch_codeforces.py
│   ├── enrich_companies.py
│   ├── aggregate_sheets.py
│   ├── build_roadmap.py
│   ├── validate_corpus.py
│   ├── export_snapshots.py
│   └── lib/
│       ├── db.py
│       ├── upsert.py
│       ├── mcp_client.py
│       ├── cf_tag_map.json
│       ├── lc_topic_map.json
│       ├── topic_editorial.json
│       └── sheet_loaders/
├── backend/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py        ← async SQLAlchemy engine → Supabase
│       ├── cache.py           ← Redis client
│       ├── routers/           ← auth, users, stats, platforms, questions, roadmap, sheet
│       ├── services/          ← leetcode, codeforces, github, intelligence, llm
│       ├── models/            ← SQLAlchemy ORM models
│       └── schemas/           ← Pydantic request/response schemas
└── frontend/
    └── src/
        ├── components/{ui,dashboard,profile,questions}
        ├── pages/             ← Login, Onboarding, Dashboard, Questions, Roadmap, Sheet, Profile
        ├── hooks/
        ├── api/
        ├── store/
        └── types/
```

---

## Database Schema (all tables in Supabase Postgres)

### User-scoped (RLS enabled)
- **users** — id, email, name, username, college, avatar_url, github_login, lc_username, cf_handle, gh_username, created_at, last_synced
- **platform_snapshots** — id, user_id, platform, raw_data (JSONB), fetched_at
- **topic_scores** — id, user_id, topic, attempted, solved, accuracy, weakness_score, computed_at
- **sheet_progress** — id, user_id, problem_id, status (todo/attempted/done), updated_at
- **question_progress** — id, user_id, question_id, status, notes, updated_at

### Corpus (public-read, written by scrapers)
- **questions** — id (lc-N / cf-NA), platform, number, title, slug, url, difficulty, difficulty_rating, statement_html, statement_text, constraints, examples, hints, is_premium, acceptance_rate, solved_count, raw (JSONB), fetched_at
- **question_topics** — question_id, topic (composite PK)
- **question_companies** — question_id, company, frequency, timeframe (composite PK)
- **roadmap_topics** — topic (PK), ordinal, display_name, prerequisite_topics[], summary, core_patterns[], starter_problems[], milestone_problems[]
- **sheet_sources** — id, name, url, problem_count, weight, fetched_at
- **sheet_source_problems** — sheet_id, question_id, position, topic_hint
- **curated_sheet** — id (optimal_mix_v1), name, description, generated_at, generator_version
- **curated_sheet_problems** — sheet_id, question_id, topic, ordinal, cross_sheet_count, source_sheets[], score
- **fetch_runs** — id, started_at, finished_at, platform, layer, status, problem_count, notes, errors

Full DDL: see `db/migrations/0001_init.sql`

---

## API Endpoint Inventory

```
GET  /health
POST /auth/github/callback
POST /auth/refresh
GET  /users/me
PATCH /users/me
GET  /users/:username/public
GET  /stats/me
POST /stats/sync
GET  /stats/:username/topics
GET  /stats/:username/readiness
GET  /questions?topic=&platform=&difficulty=&company=&q=
GET  /questions/by-topic
GET  /questions/:id
PATCH /questions/:id/progress
GET  /roadmap
GET  /sheet/curated
GET  /sheet/sources
GET  /sheet/progress/me
PATCH /sheet/progress/:problem_id
GET  /insights/readiness-summary            ← LLM 2-sentence narrative (auth)
GET  /insights/recommendations              ← LLM 3 next problems, slug-resolved (auth)
GET  /insights/topics/:topic/explain        ← LLM 1-paragraph topic-gap (auth)
```

Response envelope: `{ "success": true, "data": {...}, "meta": { "cached": bool, "fetched_at": "..." } }`

---

## External API Rules

| API | Rule |
|---|---|
| LeetCode GraphQL | Always send `Referer: https://leetcode.com`. Rate limit: max 5 concurrent, exponential backoff on 429/403. |
| Codeforces | `problemset.problems` returns all problems in one call. No auth for public data. |
| GitHub REST | Send `Authorization: Bearer {GITHUB_TOKEN}` + `Accept: application/vnd.github.v3+json`. Read-only scopes only. |
| Supabase | `SUPABASE_SERVICE_ROLE_KEY` is server/scraper only — never sent to frontend. |

---

## Redis Cache Key Conventions

| Key pattern | TTL | Contents |
|---|---|---|
| `lc:{username}` | 6h | LeetCode user stats |
| `cf:{handle}` | 6h | Codeforces user stats |
| `gh:{username}` | 6h | GitHub user stats |
| `readiness:{user_id}` | 1h | Readiness score breakdown |
| `llm:{sha256(input)}` | 24h | LLM response cached by input hash |
| `qtopic:{topic}` | 12h | Questions by-topic slice |

---

## LLM Service Contract (`backend/app/services/llm.py`)

Provider: **Gemini 2.0 Flash** (`gemini-2.0-flash`) via `GEMINI_API_KEY`. Pluggable: set `LLM_PROVIDER=groq|mistral` to swap. (The original `gemini-2.0-flash-exp` experimental alias was retired → 404; use the GA `gemini-2.0-flash`.)

Three functions only — stateless, no chat history:
1. `recommend_next_problems(weak_topics: list[str], solved_ids: set[str]) -> list[str]` — returns 3 question IDs
2. `summarize_readiness(score_breakdown: dict) -> str` — 2-sentence narrative
3. `explain_topic_gap(topic: str, accuracy: float, volume: int) -> str` — 1-paragraph

Every call is cached in Redis by `sha256(json(inputs))` with 24h TTL.

---

## DSA Topic Order (canonical sequence)

```
1. arrays
2. strings
3. hashing
4. two-pointers
5. sliding-window
6. prefix-sum
7. binary-search
8. linked-list
9. stacks-queues
10. recursion
11. backtracking
12. trees
13. bst
14. heap
15. greedy
16. dynamic-programming
17. graphs
18. tries
19. segment-trees
20. bit-manipulation
21. math
22. string-algorithms
```

---

## External DSA Sheets Aggregated (curated mix scoring)

Sheets ingested: Striver A2Z (455), Striver SDE (191), Blind 75, Neetcode 150/250/All, Grind 75/169, Love Babbar 450, LC Top Interview 150, LC Top 100 Liked, AlgoExpert 160, CSES (~400), SeanPrashad Patterns (~170), USACO Guide (~1000), A2OJ Ladders.

Scoring formula:
```
score = (2 × cross_sheet_count)
      + topic_coverage_bonus      # +1 if topic has < 8 picks
      + difficulty_balance_bonus  # +1 if keeps E:M:H ≈ 1:2:1
      + 0.5 × log(1 + company_frequency)
      + 0.5 × sum(sheet.weight for sheet in source_sheets)
```
Target: ~28 per topic (8 easy / 14 medium / 6 hard). Total ~350–450 problems.

---

## Environment Variables (names only)

### Backend (`backend/.env`)
```
DATABASE_URL=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
REDIS_URL=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_TOKEN=
JWT_SECRET=
JWT_EXPIRE_MINUTES=10080
FRONTEND_URL=http://localhost:5173
GEMINI_API_KEY=
LLM_PROVIDER=gemini
LEETCODE_SESSION=
LEETCODE_CSRF_TOKEN=
FETCH_CF_STATEMENTS=false
```

### Frontend (`frontend/.env`)
```
VITE_API_URL=http://localhost:8000
VITE_GITHUB_CLIENT_ID=
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
```

---

## DO NOT Build

- Resume scoring vs JD
- Daily email notifications
- VJTI peer comparison
- AI chatbot / free-form chat
- SQLite or any local database
- Hand-entered DSA sheets
- Browser extension
- Mobile app
- Company-specific prep tracker

---

## See Also

- Step-by-step build history: `progress.md`
- Change log: `memory.md`
- Full DDL: `db/migrations/0001_init.sql`
