# AlgoSweeped — Implementation Plan

## Context

Greenfield project at `/Users/vaishnavisanap/Desktop/name_that_folder /` (currently empty). The user (VJTI Mumbai student) has provided a master spec for **AlgoSweeped**, a developer progress dashboard aggregating LeetCode, Codeforces, and GitHub data into one place with topic-wise weakness analysis, an interview readiness score, a public profile, and a DSA sheet tracker.

This plan layers the user's **late-stage modifications** on top of that base spec:

1. **Postgres from Day 1, no SQLite anywhere.** Supabase (managed Postgres) is the canonical store from the very first commit. Schema is designed once in Postgres; scrapers write directly into Supabase; the frontend and backend build against Supabase from day one. JSON files in `data/` are *snapshots/exports*, not the source of truth.
2. **Remove** the AI chatbot. **Keep** narrow LLM calls to a free-tier model (Gemini 2.0 Flash) for specific bounded tasks (recommendations, summaries).
3. **Pre-fetch the entire question corpus** from LeetCode and Codeforces ahead of building the app — full title, number, problem statement, difficulty, topic tags, and (where available) companies that asked the question. Written directly to Supabase tables.
4. **Use the most-starred / most-actively-maintained MCP servers** for LeetCode, Codeforces, and GitHub during the data-fetch phase (and as a fallback at runtime).
5. **No hand-entered DSA sheet.** Aggregate every reputable online DSA sheet (Striver A2Z, Striver SDE, Blind 75, Neetcode 150/250/All, Grind 75/169, Love Babbar 450, LeetCode Top Interview 150, AlgoExpert 160, CSES, SeanPrashad Patterns, USACO Guide, A2OJ ladders) and compute an **optimal curated mix** weighted by cross-sheet frequency, topic coverage, and difficulty balance. The output is one unified curated sheet stored in Supabase.
6. **Author a comprehensive ordered DSA roadmap** (topics in pedagogical order) using the fetched corpus + aggregated sheets as input.
7. **Frontend topic accordion** — questions grouped under topic accordion folders (click "Strings" → expanded list of string problems).
8. Maintain three meta files:
   - `CLAUDE.md` — single source of truth for project reference data; every future Claude prompt must read this first (token-saving discipline).
   - `progress.md` — running log of every step taken, what worked, what didn't, and why.
   - `memory.md` — running log of every notable change made during development.
9. **Skip teaching/explanation prose** in code and commits — code-first.
10. **No timeline** — plan stays scope-focused, not schedule-focused.

---

## Recommended Approach

### 0. Day 1 — Supabase-first bootstrap

**Hard rule: Postgres (Supabase) is the canonical store from commit #1. SQLite is not used anywhere — not for dev, not for tests, not as a fallback.** Both the scraper and the app speak directly to Supabase.

Day-1 sequence (in this exact order):

1. **Create Supabase project** at `supabase.com` → free tier → region closest to user (likely `ap-south-1` for Mumbai). Capture:
   - `DATABASE_URL` (the asyncpg-compatible connection string from Project Settings → Database → Connection string → URI).
   - `SUPABASE_URL` and `SUPABASE_ANON_KEY` (for frontend direct reads where useful).
   - `SUPABASE_SERVICE_ROLE_KEY` (server-only, for scraper writes).
2. **Design the full schema once, in Postgres.** Apply via a single SQL migration file `db/migrations/0001_init.sql` run through the Supabase SQL editor (or `psql`). Schema covers:
   - Per the master prompt: `users`, `platform_snapshots`, `topic_scores`, `sheet_progress`.
   - Net-new: `questions`, `question_companies`, `question_topics`, `roadmap_topics`, `curated_sheet`, `curated_sheet_problems`, `sheet_sources`, `question_progress`, `fetch_runs`.
   - All tables use `UUID` primary keys, `TIMESTAMPTZ` timestamps, RLS policies where the table is user-scoped.
3. **Wire the scraper to Supabase.** Scripts in `/scripts/` connect via `DATABASE_URL` (asyncpg / SQLAlchemy core), upsert directly into `questions`, `question_topics`, `question_companies`, `sheet_sources`, `curated_sheet_problems`. JSON files under `data/` are written *only* as auditable snapshots of what went into the DB on each run.
4. **Run the scraper.** `python scripts/fetch_all.py` populates the corpus + aggregated sheets + roadmap into Supabase.
5. **Build the backend against Supabase.** `backend/app/database.py` reads `DATABASE_URL`; SQLAlchemy async session; all routers query Supabase directly. No local DB ever exists.
6. **Build the frontend against the backend from day one.** Vite dev server hits the local FastAPI which hits Supabase. No mock data layer, no hardcoded fixtures.

This ordering is non-negotiable: schema → scraper → backend → frontend. Every later lay Kon jaygayer assumes the DB is already populated.

### 0a. Repository layout

```
icode-plus/
├── CLAUDE.md                       ← reference data + read-first directive
├── progress.md                     ← step log
├── memory.md                       ← change log
├── README.md                       ← short, public-facing
│
├── db/
│   ├── migrations/
│   │   ├── 0001_init.sql           ← full Day-1 schema (every table, indexes, RLS)
│   │   └── 0002_*.sql              ← any future changes (append-only)
│   └── seed.sql                    ← seed reference rows (canonical topic vocabulary, etc.)
│
├── data/                           ← snapshots/exports only — NOT the source of truth
│   ├── snapshots/
│   │   ├── leetcode_YYYYMMDD.json  ← exported after each scraper run
│   │   └── codeforces_YYYYMMDD.json
│   ├── sheets/                     ← raw downloads of each external DSA sheet
│   │   ├── striver_a2z.json
│   │   ├── striver_sde.json
│   │   ├── blind75.json
│   │   ├── neetcode_150.json
│   │   ├── neetcode_250.json
│   │   ├── grind_75.json
│   │   ├── grind_169.json
│   │   ├── babbar_450.json
│   │   ├── lc_top_interview_150.json
│   │   ├── lc_top_100_liked.json
│   │   ├── algoexpert_160.json
│   │   ├── cses.json
│   │   ├── seanprashad_patterns.json
│   │   ├── usaco_guide.json
│   │   └── a2oj_ladders.json
│   └── _fetched_at.json            ← provenance: source, timestamp, count, layer used
│
├── scripts/                        ← one-shot tooling, writes directly to Supabase
│   ├── fetch_all.py                ← orchestrator
│   ├── fetch_leetcode.py           ← LC: GraphQL → MCP → REST wrappers → CLI → Playwright
│   ├── fetch_codeforces.py         ← CF: official API → MCP → clist.by → libs → scrape
│   ├── enrich_companies.py         ← merges open community company-tag datasets
│   ├── aggregate_sheets.py         ← downloads + normalizes external DSA sheets → curated mix
│   ├── build_roadmap.py            ← assembles ordered roadmap from corpus + sheets
│   ├── validate_corpus.py          ← schema + referential-integrity checks against Supabase
│   ├── export_snapshots.py         ← dumps DB tables to data/snapshots/*.json for audit
│   └── lib/
│       ├── db.py                   ← asyncpg/SQLAlchemy engine wired to DATABASE_URL
│       ├── upsert.py               ← idempotent upsert helpers per table
│       ├── mcp_client.py           ← thin stdio JSON-RPC client for any MCP server
│       ├── cf_tag_map.json         ← CF tag → canonical topic vocabulary
│       ├── lc_topic_map.json       ← LC topic slug → canonical topic vocabulary
│       └── sheet_loaders/          ← one file per external sheet source
│           ├── striver.py
│           ├── neetcode.py
│           ├── grind.py
│           ├── blind75.py
│           ├── babbar.py
│           ├── leetcode_official.py
│           ├── algoexpert.py
│           ├── cses.py
│           ├── seanprashad.py
│           ├── usaco_guide.py
│           └── a2oj.py
│
├── backend/                        ← FastAPI, talks to Supabase only
│   └── app/
│       ├── main.py
│       ├── routers/                ← users, stats, platforms, auth, questions, roadmap, sheet
│       ├── services/               ← leetcode, codeforces, github, intelligence, llm
│       ├── models/                 ← SQLAlchemy models mirroring the SQL migration
│       ├── schemas/                ← Pydantic
│       ├── cache.py                ← Redis (Upstash)
│       ├── database.py             ← async engine bound to Supabase DATABASE_URL
│       └── config.py
│
└── frontend/                       ← React + TS + Tailwind, talks to backend (and optionally Supabase directly for public reads)
    └── src/
        ├── components/
        │   ├── ui/
        │   ├── dashboard/
        │   ├── profile/
        │   └── questions/          ← TopicAccordion, QuestionRow, FilterBar
        ├── pages/                  ← Dashboard, Profile, Login, Onboarding, Questions, Roadmap
        ├── hooks/
        ├── api/
        ├── store/
        └── types/
```

---

### 0b. Full Postgres schema (Day-1 migration `db/migrations/0001_init.sql`)

```sql
-- USERS & PROGRESS (per master prompt, with question_progress added)
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email         TEXT UNIQUE NOT NULL,
  name          TEXT,
  username      TEXT UNIQUE NOT NULL,
  college       TEXT DEFAULT 'VJTI',
  avatar_url    TEXT,
  github_login  TEXT UNIQUE,
  lc_username   TEXT,
  cf_handle     TEXT,
  gh_username   TEXT,
  created_at    TIMESTAMPTZ DEFAULT now(),
  last_synced   TIMESTAMPTZ
);

CREATE TABLE platform_snapshots (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
  platform    TEXT NOT NULL,
  raw_data    JSONB NOT NULL,
  fetched_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON platform_snapshots(user_id, platform, fetched_at DESC);

CREATE TABLE topic_scores (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
  topic           TEXT NOT NULL,
  attempted       INT DEFAULT 0,
  solved          INT DEFAULT 0,
  accuracy        FLOAT,
  weakness_score  FLOAT,
  computed_at     TIMESTAMPTZ DEFAULT now()
);

-- CORPUS TABLES (populated by scrapers)
CREATE TABLE questions (
  id                TEXT PRIMARY KEY,                -- 'lc-1', 'cf-1A', etc.
  platform          TEXT NOT NULL,                   -- 'leetcode' | 'codeforces'
  number            TEXT,                            -- '1' for LC, '1A' for CF
  title             TEXT NOT NULL,
  slug              TEXT,
  url               TEXT NOT NULL,
  difficulty        TEXT,                            -- 'easy' | 'medium' | 'hard' (LC) | rating bucket (CF)
  difficulty_rating INT,                             -- CF numeric, null for LC
  statement_html    TEXT,
  statement_text    TEXT,
  constraints       JSONB,
  examples          JSONB,
  hints             JSONB,
  is_premium        BOOLEAN DEFAULT false,
  acceptance_rate   FLOAT,
  solved_count      INT,
  raw               JSONB,                           -- full original API/MCP payload
  fetched_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON questions(platform);
CREATE INDEX ON questions(difficulty);

CREATE TABLE question_topics (
  question_id TEXT REFERENCES questions(id) ON DELETE CASCADE,
  topic       TEXT NOT NULL,
  PRIMARY KEY (question_id, topic)
);
CREATE INDEX ON question_topics(topic);

CREATE TABLE question_companies (
  question_id TEXT REFERENCES questions(id) ON DELETE CASCADE,
  company     TEXT NOT NULL,
  frequency   INT,
  timeframe   TEXT,                                  -- '30d' | '3mo' | '6mo' | 'all'
  PRIMARY KEY (question_id, company, timeframe)
);
CREATE INDEX ON question_companies(company);

-- ROADMAP (one row per canonical topic, ordered)
CREATE TABLE roadmap_topics (
  topic              TEXT PRIMARY KEY,
  ordinal            INT NOT NULL UNIQUE,
  display_name       TEXT NOT NULL,
  prerequisite_topics TEXT[],
  summary            TEXT,
  core_patterns      TEXT[],
  starter_problems   TEXT[],
  milestone_problems TEXT[]
);

-- AGGREGATED SHEETS
CREATE TABLE sheet_sources (
  id          TEXT PRIMARY KEY,                      -- 'striver_a2z', 'blind75', etc.
  name        TEXT NOT NULL,
  url         TEXT,
  problem_count INT,
  weight      FLOAT DEFAULT 1.0,                     -- editorial weight in optimal-mix score
  fetched_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE sheet_source_problems (
  sheet_id   TEXT REFERENCES sheet_sources(id) ON DELETE CASCADE,
  question_id TEXT REFERENCES questions(id) ON DELETE CASCADE,
  position   INT,                                    -- order within that sheet
  topic_hint TEXT,                                   -- the topic the sheet itself assigns
  PRIMARY KEY (sheet_id, question_id)
);

CREATE TABLE curated_sheet (
  id           TEXT PRIMARY KEY DEFAULT 'optimal_mix_v1',
  name         TEXT NOT NULL,
  description  TEXT,
  generated_at TIMESTAMPTZ DEFAULT now(),
  generator_version TEXT
);

CREATE TABLE curated_sheet_problems (
  sheet_id      TEXT REFERENCES curated_sheet(id) ON DELETE CASCADE,
  question_id   TEXT REFERENCES questions(id) ON DELETE CASCADE,
  topic         TEXT NOT NULL,
  ordinal       INT NOT NULL,                        -- order within topic
  cross_sheet_count INT,                             -- how many external sheets included this
  source_sheets TEXT[],                              -- which sheets it came from
  score         FLOAT,                               -- optimal-mix score
  PRIMARY KEY (sheet_id, question_id)
);
CREATE INDEX ON curated_sheet_problems(sheet_id, topic, ordinal);

-- USER PROGRESS (per master prompt + new question_progress)
CREATE TABLE sheet_progress (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
  problem_id  TEXT NOT NULL,
  status      TEXT DEFAULT 'todo',
  updated_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, problem_id)
);

CREATE TABLE question_progress (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
  question_id TEXT REFERENCES questions(id) ON DELETE CASCADE,
  status      TEXT DEFAULT 'todo',
  notes       TEXT,
  updated_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, question_id)
);

-- SCRAPER AUDIT
CREATE TABLE fetch_runs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  started_at  TIMESTAMPTZ DEFAULT now(),
  finished_at TIMESTAMPTZ,
  platform    TEXT,                                  -- 'leetcode' | 'codeforces' | 'sheets'
  layer       TEXT,                                  -- which alternate-flow layer succeeded
  status      TEXT,                                  -- 'ok' | 'partial' | 'failed'
  problem_count INT,
  notes       TEXT,
  errors      JSONB
);

-- RLS: user-scoped tables protected so a logged-in user can only see their own rows
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE topic_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE sheet_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_progress ENABLE ROW LEVEL SECURITY;
-- (policies attached in 0001_init.sql; corpus + sheet tables are public-read.)
```

---

### 1. Pre-fetched question corpus (one-time scripts → Supabase)

Run **before** building the app. Output is written **directly into Supabase** (`questions`, `question_topics`, `question_companies`); a parallel JSON snapshot is dropped into `data/snapshots/` for audit only. Each fetcher script implements a **layered strategy**: try the main flow first; on failure (rate limit, auth wall, empty response, schema mismatch) automatically fall back to the next layer. Every layer's success/failure is recorded as a row in `fetch_runs` and mirrored to `data/_fetched_at.json`.

#### 1a. LeetCode (`scripts/fetch_leetcode.py`)

**Goal output schema per problem:**
```json
{
  "platform": "leetcode",
  "id": "lc-1",
  "number": 1,
  "title": "Two Sum",
  "slug": "two-sum",
  "url": "https://leetcode.com/problems/two-sum/",
  "difficulty": "easy",
  "statement_html": "<p>Given an array...</p>",
  "statement_text": "Given an array...",
  "topics": ["arrays", "hash-table"],
  "companies": [{"name": "Amazon", "frequency": 87}, ...],
  "constraints": ["2 <= nums.length <= 10^4"],
  "examples": [{"input": "...", "output": "...", "explanation": "..."}],
  "hints": ["..."],
  "is_premium": false,
  "acceptance_rate": 0.523,
  "frontend_id": "1"
}
```

**Main flow — LeetCode official GraphQL (`https://leetcode.com/graphql`):**
1. Bulk list: `problemsetQuestionList(categorySlug: "", limit: 5000, skip: 0, filters: {})` → returns every problem's `questionFrontendId`, `title`, `titleSlug`, `difficulty`, `topicTags`, `acRate`, `paidOnly`.
2. Per-problem detail (only for non-premium, or all if a logged-in session cookie is available): `questionData(titleSlug: $slug)` → returns `content` (HTML statement), `hints`, `exampleTestcases`, `sampleTestCase`, `metaData`, `codeSnippets`.
3. Companies (premium gate): `questionCompanyTags(titleSlug: $slug)` — works only with an authenticated `LEETCODE_SESSION` + `csrftoken` cookie. If cookies are present in env, use them; otherwise companies come from the open-dataset layer below.
4. **Headers required** (or LC blocks):
   ```
   Referer: https://leetcode.com
   User-Agent: Mozilla/5.0 (...)
   x-csrftoken: {from cookie if present}
   Cookie: LEETCODE_SESSION=...; csrftoken=...  (optional, unlocks premium fields)
   ```
5. **Rate-limit handling**: async `httpx` with semaphore (max 5 concurrent), exponential backoff on 429/403, 50ms jitter between requests. Persist progress to a checkpoint file every 50 problems — resumable.

**Alternate flow 1 — LeetCode MCP servers** (try in this order, picking whichever has the highest current star count at fetch time):
1. `jinzcdev/leetcode-mcp-server` — exposes `get_problem`, `search_problems`, `get_user_profile`, `get_daily_challenge` tools.
2. `doggybee/mcp-server-leetcode` — TypeScript implementation, similar tool surface.
3. `IanLin1518/leetcode-mcp` — alternate implementation.
4. `mcp-leetcode` from any active fork newer than the above (script does `gh search repos "leetcode mcp"` sorted by stars at fetch time to discover newer entrants).

MCP path is invoked via a thin wrapper: spawn the MCP server as a subprocess, talk to it over stdio JSON-RPC, call tools, harvest results. Same schema as the GraphQL output.

**Alternate flow 2 — Hosted REST wrappers** (no auth needed, useful as a fast bulk source):
1. `alfaarghya/alfa-leetcode-api` — hosted at `https://alfa-leetcode-api.onrender.com` (and self-hostable). Endpoints: `/problems`, `/select?titleSlug=`, `/{username}`.
2. `JeremyTsaii/leetcode-stats-api` — `https://leetcode-stats-api.herokuapp.com/{username}`.
3. `leetcode-api-faisalshohag` — community fork with similar surface.

**Alternate flow 3 — Open-source CLI tools** (run locally, dump JSON):
1. `skygragon/leetcode-cli` — `leetcode list -q L > problems.json`, supports login for premium content.
2. `leetcode-export` (PyPI) — exports submissions + problem metadata.
3. `clemenspeters/leetcode-graphql` — typed GraphQL client used as a library.

**Alternate flow 4 — Browser automation** (last resort for premium-gated fields):
1. Playwright (`playwright-python`) with a logged-in storage state file; navigate to `https://leetcode.com/problems/{slug}/`, parse the rendered DOM, extract company chips from the right panel.
2. Selenium equivalent if Playwright unavailable.
3. Throttle hard (1 req / 2 sec) — this path is bandwidth-cheap but slow and only used for problems where companies are missing after layers 1–3.

**Companies enrichment — dataset layer (`scripts/enrich_companies.py`):**
LC company tags are premium-locked. Even with paid auth, frequency data is incomplete. So `companies` is always cross-referenced against open community datasets:
1. `liquidslr/leetcode-company-wise-problems` — JSON/CSV per company.
2. `krishnadey30/LeetCode-Questions-CompanyWise` — CSV files per company × timeframe (30d/3mo/6mo/all).
3. `hxu296/leetcode-company-wise-problems-2022` — historical dump.
4. `noisefilter19/LeetCode_Companies` — supplementary.
5. `seanprashad/leetcode-patterns` — patterns + companies overlay (used also for topic-pattern enrichment).

Script downloads each repo's latest release/main, normalizes per-company CSVs into a unified `{slug: [{name, frequency, timeframe}]}` map, and merges into the corpus. Conflicts: prefer the most recent timeframe. Missing companies on a problem → empty list (not an error).

**Premium problem handling:** `is_premium: true` problems get title/topics/difficulty from the list query but `statement_html` will be `null` unless an authenticated session is provided. The corpus marks them clearly so the UI can show a "Premium — view on LeetCode" badge.

#### 1b. Codeforces (`scripts/fetch_codeforces.py`)

**Goal output schema per problem:**
```json
{
  "platform": "codeforces",
  "id": "cf-1A",
  "contest_id": 1,
  "index": "A",
  "title": "Theatre Square",
  "url": "https://codeforces.com/problemset/problem/1/A",
  "difficulty_rating": 1000,
  "topics": ["math", "implementation"],
  "companies": [],
  "statement_text": null,
  "solved_count": 187432,
  "type": "PROGRAMMING"
}
```

Per the resolved decision above, CF stores **metadata + link-out** by default. The alternate flows below are available for users who want full statement text in the corpus later.

**Main flow — Codeforces official API** (`https://codeforces.com/api/`):
1. `problemset.problems` — single call returns *all* problems with `contestId`, `index`, `name`, `type`, `rating`, `tags[]`, plus a parallel `problemStatistics[]` array with `solvedCount`. No auth required, no rate limit beyond "be reasonable".
2. Normalize: map CF's `tags` (e.g. `dp`, `graphs`, `binary search`, `dsu`) onto the project's canonical topic vocabulary (handled in `scripts/build_roadmap.py` via a `cf_tag_map.json` lookup).
3. URL is deterministic: `https://codeforces.com/problemset/problem/{contestId}/{index}`.

**Alternate flow 1 — Codeforces MCP servers:**
1. `GeorgeOduor/codeforces-mcp` and similar community MCPs (discovered via `gh search repos "codeforces mcp"` sorted by stars at fetch time).
2. The CF MCP ecosystem is small; in practice the official API is so clean that MCP offers little advantage. Listed for completeness.

**Alternate flow 2 — clist.by aggregator API** (`https://clist.by/api/v4/`):
1. Free API key (sign-up). Endpoints: `/problem/`, `/contest/`, `/account/`. Covers CF, AtCoder, LC, and 50+ judges in one schema.
2. Useful as a cross-check on tags + rating; also the only easy way to enrich CF problems with cross-platform difficulty estimates.

**Alternate flow 3 — Open-source CF libraries:**
1. `codeforces-api-py` (PyPI) — typed wrapper over the official API.
2. `cf-tool` (xalanq, Go binary) — `cf race`, `cf submit`, also exposes problem metadata locally.
3. `Competitive-Companion` browser extension format — produces standardized JSON for any CP problem; if a user has it installed, parsed exports drop into the corpus directly.
4. `kenkoooo`-style aggregators — community Codeforces problem dashboards with downloadable JSON.

**Alternate flow 4 — Full statement scraping** (opt-in, off by default):
1. HTTP GET `https://codeforces.com/problemset/problem/{contestId}/{index}` with a realistic `User-Agent` and a tiny request delay (CF tolerates polite scraping).
2. Parse with BeautifulSoup: `.problem-statement` div → `.header` (title, time/memory limits), `.input-specification`, `.output-specification`, `.sample-tests`, `.note`. Statements are LaTeX-rendered via MathJax — preserve raw HTML with `\(...\)` math markers so the frontend can re-render.
3. If Cloudflare ever fires, escalate to `cloudscraper` (PyPI) or Playwright with a stealth plugin.
4. Toggle: `FETCH_CF_STATEMENTS=true` env var on the script. Output writes `statement_html` + `statement_text` fields. Adds ~2 hours to a full pull.

**Alternate flow 5 — Open datasets:**
1. Kaggle has Codeforces problem dumps (search "codeforces problems dataset") — useful when API is down or for historical snapshots.
2. `agarwalsahil/codeforces-problems` and similar GitHub repos host periodic JSON dumps.

**Companies for CF:** Codeforces doesn't tag problems by company. The `companies` field stays `[]` for CF entries. The UI hides the company chip column when all rows in a topic accordion are CF-only.

#### 1c. Orchestrator (`scripts/fetch_all.py`)

Single entrypoint, writes directly to Supabase:

```
1. apply db/migrations/0001_init.sql (idempotent, no-op if already applied)
2. scripts/fetch_leetcode.py     → upserts into questions, question_topics
3. scripts/fetch_codeforces.py   → upserts into questions, question_topics
4. scripts/enrich_companies.py   → upserts into question_companies
5. scripts/aggregate_sheets.py   → upserts sheet_sources, sheet_source_problems, curated_sheet*
6. scripts/build_roadmap.py      → upserts into roadmap_topics
7. scripts/validate_corpus.py    → integrity check against the live Supabase tables
8. scripts/export_snapshots.py   → writes data/snapshots/*.json for audit
9. INSERT INTO fetch_runs        → final run summary row
```

Each layer's status is recorded in `fetch_runs` so a future run can see e.g. "MCP layer failed with timeout; GraphQL succeeded for 3,124 problems; Playwright filled companies for 412 of them; dataset layer added companies for the remaining 1,892."

**GitHub** has no "questions" — confirmed: only profile/repo/activity data is fetched at runtime per the master prompt.

---

### 2. Aggregated DSA sheets — the "optimal mix" (`scripts/aggregate_sheets.py`)

**No hand-entered sheet.** This script downloads every well-known online DSA sheet, normalizes problems to canonical `question_id`s (resolving against the `questions` table), records each source in `sheet_sources` / `sheet_source_problems`, then computes a single curated sheet stored in `curated_sheet` + `curated_sheet_problems`.

**External sheets ingested** (one loader per source under `scripts/lib/sheet_loaders/`):

| Source | Approx. count | Loader path / URL |
|---|---|---|
| Striver A2Z (takeuforward) | 455 | Public JSON via tuf-graphql / community mirrors on GitHub |
| Striver SDE Sheet | 191 | tuf-graphql / community JSON |
| Blind 75 | 75 | `teivah/algodeck`, `neetcode.io/practice` exports |
| Neetcode 150 | 150 | `neetcode.io` public JSON |
| Neetcode 250 | 250 | `neetcode.io` public JSON |
| Neetcode All | ~500 | `neetcode.io` public JSON |
| Grind 75 | 75 | `techinterviewhandbook.org` (open-source, MIT) |
| Grind 169 | 169 | `techinterviewhandbook.org` |
| Love Babbar 450 | 450 | Public JSON mirrors (multiple GitHub repos) |
| LeetCode Top Interview 150 | 150 | LC GraphQL `studyPlanV2Detail(slug: "top-interview-150")` |
| LeetCode Top 100 Liked | 100 | LC GraphQL same study-plan API |
| AlgoExpert 160 | 160 | Community JSON dumps (no official API) |
| CSES Problem Set | ~400 | Scrape `cses.fi/problemset/` (HTML, very stable) |
| SeanPrashad Patterns | ~170 | `seanprashad/leetcode-patterns` JSON in repo |
| USACO Guide | ~1000 | `cpinitiative/usaco-guide` repo (open data) |
| A2OJ Ladders (CF) | varies | `a2oj.com` ladder pages, community mirrors |

Each loader returns the same normalized record:
```python
{
  "sheet_id": "neetcode_150",
  "external_problem_ref": "two-sum",        # whatever the sheet calls it
  "platform_hint": "leetcode",
  "position": 1,
  "topic_hint": "Arrays & Hashing"
}
```

The orchestrator resolves `external_problem_ref` → canonical `question_id` (by slug for LC, by `{contest_id}-{index}` for CF). Unresolvable refs are logged but not fatal.

**Optimal-mix scoring** (computed per problem after all sheets are ingested):
```
cross_sheet_count = number of distinct sheets including this problem
topic_coverage_bonus = +1 if this problem is in an undersupplied topic (fewer than 8 picks so far)
difficulty_balance_bonus = +1 if including this problem keeps per-topic E/M/H roughly 1:2:1
company_signal = log(1 + total_company_frequency) when available
editorial_weight = sum of sheet_sources.weight for the sheets that include it

score = (2 * cross_sheet_count)
      + topic_coverage_bonus
      + difficulty_balance_bonus
      + 0.5 * company_signal
      + 0.5 * editorial_weight
```

Selection: greedy per topic — walk topics in roadmap order, pick the top-scoring problems for that topic until the per-topic quota is met (default: 8 easy / 14 medium / 6 hard = 28 per topic), skipping problems already chosen. Final curated mix lands around 350–450 problems and is written to `curated_sheet_problems` with `sheet_id = 'optimal_mix_v1'`.

Output is deterministic given the same inputs (sorted tiebreakers on `question_id`) so re-runs produce stable diffs.

---

### 3. DSA Roadmap (Postgres `roadmap_topics` table)

The roadmap lives in Supabase, not as a JSON file. `scripts/build_roadmap.py` writes one row per canonical topic.

Topic ordering (no learning prose — just the order):
`arrays → strings → hashing → two-pointers → sliding-window → prefix-sum → binary-search → linked-list → stacks-queues → recursion → backtracking → trees → bst → heap → greedy → dynamic-programming → graphs → tries → segment-trees → bit-manipulation → math → string-algorithms`

For each topic, the builder populates:
- `starter_problems` — lowest-difficulty 3 from the curated mix.
- `milestone_problems` — top 3 by company-frequency within the topic.
- `core_patterns`, `prerequisite_topics`, `summary` — seeded from a small editorial JSON (`scripts/lib/topic_editorial.json`) and merged in.

---

### 4. Backend (FastAPI against Supabase)

`backend/app/database.py` builds an async SQLAlchemy engine from `DATABASE_URL` (Supabase connection string). No SQLite, no local file DB.

**New routers** (on top of the master prompt's):
- `routers/questions.py`
  - `GET /questions?topic=&platform=&difficulty=&company=&q=` — paginated, filterable; reads from `questions` + `question_topics` + `question_companies`.
  - `GET /questions/by-topic` — returns topic → problems map shaped for the frontend accordion.
  - `GET /questions/{id}` — single problem with full statement.
  - `PATCH /questions/{id}/progress` — upsert `question_progress`.
- `routers/roadmap.py`
  - `GET /roadmap` — returns `roadmap_topics` rows joined with the current user's per-topic progress.
- `routers/sheet.py` (replaces the master prompt's `sheet` router — same surface, different backing):
  - `GET /sheet/curated` — returns the optimal-mix curated sheet grouped by topic.
  - `GET /sheet/sources` — lists `sheet_sources` (so the UI can show "this curated mix draws from Neetcode 150 + Striver A2Z + …").
  - `GET /sheet/progress/me` — current user's completion across the curated sheet.
  - `PATCH /sheet/progress/:problem_id` — upsert into `sheet_progress`.

**New service:**
- `services/llm.py` — single narrow LLM client. **Replaces** the chatbot idea.
  - Provider: Gemini 2.0 Flash (`gemini-2.0-flash-exp` via Google AI Studio free tier). Pluggable via env var.
  - Bounded functions:
    1. `recommend_next_problems(weak_topics, solved_ids) -> list[str]`
    2. `summarize_readiness(score_breakdown) -> str`
    3. `explain_topic_gap(topic, accuracy, volume) -> str`
  - Stateless, no chat history, cached in Redis by input hash.

**MCP usage at runtime:** optional, env-flagged. Primary runtime path is direct HTTP to LC/CF/GitHub; MCPs are a fallback.

---

### 5. Frontend (React + TS + Tailwind, talks to backend)

**New pages:**
- `pages/Questions.tsx` — full corpus, topic-accordion view.
- `pages/Roadmap.tsx` — ordered roadmap stepper; each topic links into the Questions accordion pre-expanded.
- `pages/Sheet.tsx` — the curated optimal-mix sheet (replaces the master prompt's Sheet Tracker), with a "Sources" badge row that shows which external sheets contributed.

**New components** in `components/questions/`:
- `<TopicAccordion />` — collapsible topic folders. Each header: topic name, count, user's done/total badge, weakness-score color dot.
- `<QuestionRow />` — problem number, title, difficulty pill, platform badge, company chips (collapsed by default), status checkbox (todo/attempted/done), external link.
- `<QuestionFilterBar />` — filter by difficulty, platform, company; search by title. Applies across all open accordions.
- `<RoadmapNav />` — left rail listing the ordered roadmap; clicking a topic scrolls/jumps to that accordion section.
- `<SheetSourceBadges />` — shows which external sheets a problem came from (e.g. "in Neetcode 150 + Blind 75 + Striver A2Z").

**Data flow:**
- On page load: `GET /questions/by-topic` once → cached in React Query.
- Status updates: `PATCH /questions/{id}/progress` → optimistic update.
- Curated sheet: `GET /sheet/curated` → grouped by topic, ordered by `curated_sheet_problems.ordinal`.

**Dashboard tie-in:** the existing dashboard's `<TopicTable />` rows become clickable → deep-link to `/questions?topic={topic}` with that accordion pre-expanded.

---

### 6. Meta files

**`CLAUDE.md`** — must contain, in order:
1. **Read-first directive** (top of file, bold): "Every prompt working on this project MUST read this file first and use it as the source of project reference data. Do not re-fetch information that lives here. This saves tokens and keeps decisions consistent."
2. Project summary (2–3 sentences).
3. Tech stack (exact versions where pinned). Includes: **Postgres via Supabase is the only datastore — no SQLite, no local DB.**
4. Folder structure (the tree above).
5. Database schema — the full Day-1 migration: `users`, `platform_snapshots`, `topic_scores`, `questions`, `question_topics`, `question_companies`, `roadmap_topics`, `sheet_sources`, `sheet_source_problems`, `curated_sheet`, `curated_sheet_problems`, `sheet_progress`, `question_progress`, `fetch_runs`.
6. API endpoint inventory (one-line per endpoint).
7. External API rules (LeetCode `Referer` header, GitHub token scope, CF rate limits, Supabase service-role key is server-only).
8. Redis cache key conventions and TTLs.
9. LLM service contract (the three bounded functions + provider).
10. DSA topic order (the canonical sequence).
11. List of external DSA sheets aggregated into the curated mix + the mix-scoring formula.
12. Environment variables (names only, no values): `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `REDIS_URL`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_TOKEN`, `JWT_SECRET`, `GEMINI_API_KEY`, `LEETCODE_SESSION` (optional), `CSRF_TOKEN` (optional).
13. **"Do NOT build" list** — resume scoring, daily email, peer comparison, AI chatbot, **SQLite/local DB**, hand-entered DSA sheets, etc.
14. Pointer: "For step-by-step history see `progress.md`. For change log see `memory.md`."

**`progress.md`** — append-only step log. Each entry:
```
## YYYY-MM-DD — <short step name>
**Did:** <what was attempted>
**Result:** <worked / partially worked / failed>
**Why (if failed):** <root cause>
**Next:** <follow-up>
```
Seed file with a stub first entry: "Repository initialized; CLAUDE.md, progress.md, memory.md created."

**`memory.md`** — append-only change log. Each entry:
```
## YYYY-MM-DD HH:MM — <change title>
- **Scope:** <files/areas touched>
- **Change:** <one-line summary>
- **Reason:** <why>
```
Distinct from `progress.md`: progress is *narrative* (what was attempted + outcome); memory is *factual* (what concretely changed in the codebase). Both are committed.

---

### 7. Critical files to modify / create

Net-new files (all created during build):
- `CLAUDE.md`, `progress.md`, `memory.md`, `README.md`
- `db/migrations/0001_init.sql`, `db/seed.sql`
- `data/snapshots/*.json` (generated), `data/sheets/*.json` (downloaded), `data/_fetched_at.json`
- `scripts/fetch_all.py`, `scripts/fetch_leetcode.py`, `scripts/fetch_codeforces.py`, `scripts/enrich_companies.py`, `scripts/aggregate_sheets.py`, `scripts/build_roadmap.py`, `scripts/validate_corpus.py`, `scripts/export_snapshots.py`
- `scripts/lib/db.py`, `scripts/lib/upsert.py`, `scripts/lib/mcp_client.py`, `scripts/lib/cf_tag_map.json`, `scripts/lib/lc_topic_map.json`, `scripts/lib/topic_editorial.json`
- `scripts/lib/sheet_loaders/{striver,neetcode,grind,blind75,babbar,leetcode_official,algoexpert,cses,seanprashad,usaco_guide,a2oj}.py`
- `backend/app/database.py` (async engine bound to `DATABASE_URL`)
- `backend/app/routers/questions.py`, `backend/app/routers/roadmap.py`, `backend/app/routers/sheet.py`
- `backend/app/services/llm.py`
- `backend/app/models/{question.py,question_progress.py,roadmap.py,sheet.py}`
- `frontend/src/pages/Questions.tsx`, `frontend/src/pages/Roadmap.tsx`, `frontend/src/pages/Sheet.tsx`
- `frontend/src/components/questions/{TopicAccordion,QuestionRow,QuestionFilterBar,RoadmapNav,SheetSourceBadges}.tsx`

All other files (per the master prompt's structure) are also created but follow the spec already provided in that prompt — minus any reference to local/SQLite databases or hand-entered sheets.

---

### 8. Verification

End-to-end checks once built:

1. **Supabase reachability** — `psql $DATABASE_URL -c "\dt"` lists every Day-1 table; `SELECT count(*) FROM questions;` returns > 0 after the scraper run; no SQLite file exists anywhere in the repo (`find . -name '*.sqlite*' -o -name '*.db'` returns empty).
2. **Corpus integrity** — `python scripts/validate_corpus.py` queries Supabase directly and confirms: every `questions` row has non-null `id`, `title`, `difficulty`; every `question_topics.topic` value appears in `roadmap_topics`; no duplicate `questions.id`; `fetch_runs` has a recent `status='ok'` row per platform.
3. **Layered-fetch resilience** — run `python scripts/fetch_all.py --dry-run --break-layer graphql` to simulate the LC GraphQL layer failing; verify the MCP layer takes over automatically. Repeat for CF, breaking the official API to verify clist.by fallback. Each layer transition writes a row to `fetch_runs`.
4. **Optimal-mix sanity** — `SELECT topic, count(*) FROM curated_sheet_problems WHERE sheet_id='optimal_mix_v1' GROUP BY topic;` shows every roadmap topic represented; `SELECT count(DISTINCT question_id) FROM sheet_source_problems;` is materially larger than `count(*)` from any single source sheet (proving aggregation actually happened).
5. **Backend smoke** — `GET /health` → 200; `GET /questions?topic=arrays` returns rows from Supabase; `GET /roadmap` returns the ordered list; `GET /sheet/curated` returns the optimal mix grouped by topic; `GET /sheet/sources` lists every external sheet ingested.
6. **Frontend smoke** — `/questions` page renders all accordion folders collapsed; clicking "Strings" expands and shows string problems; difficulty filter narrows results; clicking the status checkbox persists across reload (round-trips through Supabase). `/sheet` page shows the curated mix with source badges.
7. **LLM smoke** — `recommend_next_problems(["dynamic-programming"], set())` returns 3 valid problem IDs that exist in `questions`; second call within TTL hits Redis cache.
8. **Meta-file discipline** — open a fresh Claude session, give it any project task; verify it reads `CLAUDE.md` first.
9. **Dashboard integration** — clicking a row in `<TopicTable />` lands on the Questions page with the matching accordion open.

---

## Resolved Decisions

1. **GitHub scope** — profile/activity only. GitHub is *not* part of the question corpus. Pre-fetch covers LeetCode + Codeforces.
2. **LLM provider** — Gemini 2.0 Flash (Google AI Studio free tier) is the default for `services/llm.py`. Interface is pluggable via env var so Groq/Mistral can swap in later.
3. **Codeforces statements** — metadata + link-out only. CF problems store number, title, tags, rating, URL. No statement scraping. `statement_text` field stays `null` for CF entries; users follow the URL to read the problem on codeforces.com.
