# AlgoSweeped

Developer progress dashboard for CS students preparing for tech internships.

Aggregates LeetCode, Codeforces, and GitHub data into one place — topic-wise weakness analysis, interview readiness score, public shareable profile, and a curated DSA sheet tracker built from 15+ online sheets.

## Stack

React + TypeScript + Tailwind — FastAPI — Postgres (Supabase) — Redis (Upstash)

## Local Setup

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in values
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
cp .env.example .env   # fill in values
npm run dev
```

## Architecture

See `CLAUDE.md` for full reference (schema, API inventory, env vars, etc.)
