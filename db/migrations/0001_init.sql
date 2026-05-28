-- iCode++ Day-1 schema
-- Run once in Supabase SQL editor (or psql $DATABASE_URL -f db/migrations/0001_init.sql)
-- Idempotent: all statements use IF NOT EXISTS where possible.

-- ─── Extensions ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── USERS ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
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
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_synced   TIMESTAMPTZ
);

-- ─── PLATFORM SNAPSHOTS ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS platform_snapshots (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  platform    TEXT NOT NULL CHECK (platform IN ('leetcode','codeforces','github')),
  raw_data    JSONB NOT NULL,
  fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS platform_snapshots_user_platform_idx
  ON platform_snapshots(user_id, platform, fetched_at DESC);

-- ─── TOPIC SCORES ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS topic_scores (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  topic           TEXT NOT NULL,
  attempted       INT NOT NULL DEFAULT 0,
  solved          INT NOT NULL DEFAULT 0,
  accuracy        FLOAT,
  weakness_score  FLOAT,
  computed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── QUESTIONS (corpus) ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS questions (
  id                TEXT PRIMARY KEY,          -- 'lc-1', 'cf-1A'
  platform          TEXT NOT NULL CHECK (platform IN ('leetcode','codeforces')),
  number            TEXT,
  title             TEXT NOT NULL,
  slug              TEXT,
  url               TEXT NOT NULL,
  difficulty        TEXT,                       -- 'easy'|'medium'|'hard' or CF bucket
  difficulty_rating INT,                        -- CF numeric rating, null for LC
  statement_html    TEXT,
  statement_text    TEXT,
  constraints       JSONB,
  examples          JSONB,
  hints             JSONB,
  is_premium        BOOLEAN NOT NULL DEFAULT false,
  acceptance_rate   FLOAT,
  solved_count      INT,
  raw               JSONB,
  fetched_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS questions_platform_idx ON questions(platform);
CREATE INDEX IF NOT EXISTS questions_difficulty_idx ON questions(difficulty);

-- ─── QUESTION TOPICS ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS question_topics (
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  topic       TEXT NOT NULL,
  PRIMARY KEY (question_id, topic)
);
CREATE INDEX IF NOT EXISTS question_topics_topic_idx ON question_topics(topic);

-- ─── QUESTION COMPANIES ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS question_companies (
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  company     TEXT NOT NULL,
  frequency   INT,
  timeframe   TEXT CHECK (timeframe IN ('30d','3mo','6mo','all')),
  PRIMARY KEY (question_id, company, timeframe)
);
CREATE INDEX IF NOT EXISTS question_companies_company_idx ON question_companies(company);

-- ─── ROADMAP TOPICS ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roadmap_topics (
  topic               TEXT PRIMARY KEY,
  ordinal             INT NOT NULL UNIQUE,
  display_name        TEXT NOT NULL,
  prerequisite_topics TEXT[],
  summary             TEXT,
  core_patterns       TEXT[],
  starter_problems    TEXT[],
  milestone_problems  TEXT[]
);

-- ─── SHEET SOURCES ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sheet_sources (
  id            TEXT PRIMARY KEY,    -- 'striver_a2z', 'blind75', etc.
  name          TEXT NOT NULL,
  url           TEXT,
  problem_count INT,
  weight        FLOAT NOT NULL DEFAULT 1.0,
  fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── SHEET SOURCE PROBLEMS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sheet_source_problems (
  sheet_id    TEXT NOT NULL REFERENCES sheet_sources(id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  position    INT,
  topic_hint  TEXT,
  PRIMARY KEY (sheet_id, question_id)
);

-- ─── CURATED SHEET ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS curated_sheet (
  id                TEXT PRIMARY KEY DEFAULT 'optimal_mix_v1',
  name              TEXT NOT NULL,
  description       TEXT,
  generated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  generator_version TEXT
);

CREATE TABLE IF NOT EXISTS curated_sheet_problems (
  sheet_id          TEXT NOT NULL REFERENCES curated_sheet(id) ON DELETE CASCADE,
  question_id       TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  topic             TEXT NOT NULL,
  ordinal           INT NOT NULL,
  cross_sheet_count INT,
  source_sheets     TEXT[],
  score             FLOAT,
  PRIMARY KEY (sheet_id, question_id)
);
CREATE INDEX IF NOT EXISTS curated_sheet_problems_topic_idx
  ON curated_sheet_problems(sheet_id, topic, ordinal);

-- ─── USER SHEET PROGRESS ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sheet_progress (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  problem_id  TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','attempted','done')),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, problem_id)
);

-- ─── USER QUESTION PROGRESS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS question_progress (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
  status      TEXT NOT NULL DEFAULT 'todo' CHECK (status IN ('todo','attempted','done')),
  notes       TEXT,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, question_id)
);

-- ─── SCRAPER AUDIT ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fetch_runs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  started_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at   TIMESTAMPTZ,
  platform      TEXT,   -- 'leetcode'|'codeforces'|'sheets'|'roadmap'
  layer         TEXT,   -- which alternate-flow layer succeeded
  status        TEXT CHECK (status IN ('ok','partial','failed')),
  problem_count INT,
  notes         TEXT,
  errors        JSONB
);

-- ─── ROW LEVEL SECURITY ──────────────────────────────────────────────────────
ALTER TABLE users             ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE topic_scores      ENABLE ROW LEVEL SECURITY;
ALTER TABLE sheet_progress    ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_progress ENABLE ROW LEVEL SECURITY;

-- Users can only read/write their own row
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='users_self' AND tablename='users') THEN
    CREATE POLICY "users_self" ON users USING (auth.uid() = id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='snapshots_self' AND tablename='platform_snapshots') THEN
    CREATE POLICY "snapshots_self" ON platform_snapshots USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='topic_scores_self' AND tablename='topic_scores') THEN
    CREATE POLICY "topic_scores_self" ON topic_scores USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='sheet_progress_self' AND tablename='sheet_progress') THEN
    CREATE POLICY "sheet_progress_self" ON sheet_progress USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname='question_progress_self' AND tablename='question_progress') THEN
    CREATE POLICY "question_progress_self" ON question_progress USING (auth.uid() = user_id);
  END IF;
END $$;
