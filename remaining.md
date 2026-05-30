# AlgoSweeped — Remaining Steps

Snapshot as of 2026-05-30. Source of truth for what's left; see `step6.md` for full specs.

## 🔴 Security / config (do first)
- [ ] **Rotate leaked secrets** — `backend/.env.example` is committed to git with REAL values
  (DATABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GITHUB_TOKEN, JWT_SECRET, REDIS_URL). Rotate all of them.
- [ ] **Scrub `backend/.env.example`** down to placeholders and keep it tracked; ensure real values
  live only in the gitignored `backend/.env`.
- [ ] **Add `GEMINI_API_KEY`** to `backend/.env` (currently empty → LLM 429/empty; fallbacks cover it
  but real LLM text needs the key + quota).

## 🟠 Dev-environment fixes
- [ ] **Fix the README local-setup steps** — they break this machine:
  - `python -m venv .venv` uses default Python **3.14**, but the venv must be **3.9.6** (recreating
    it corrupts the working venv).
  - `pip install -r requirements.txt` fails (httpx 0.28.1 vs supabase 2.4.6 pin conflict).
  - Document: reuse the existing `backend/.venv` (3.9.6); skip venv-create + pip-install if present.
- [ ] **Reconcile `requirements.txt`** with what's actually installed/working in `backend/.venv`
  (pins are 3.14-era and conflict; the running deps are fastapi 0.111, httpx 0.27, sqlalchemy 2.0.30,
  etc.). Decide: pin to working set, or fix the conflict.

## 🟡 step6.md — Part 1 bug fixes (DONE — Step 7 Part 1, 2026-05-30)
- [x] **Fix 1 — Public Profile page** — `Profile.tsx` reads `:username`; own=editable, other=read-only
  via `getPublicProfile()` (added to `api/auth.ts`); GitHub via `github_login` (added to `User` type);
  404 → "User not found".
- [x] **Fix 2 — Sheet progress cache bust** — `routers/sheet.py` busts `stats:{uid}`+`readiness:{uid}`
  after commit.
- [x] **Fix 3 — Topic-gap bogus accuracy** — `insights.py` passes `mastery = 1 - weakness_score`;
  `llm.explain_topic_gap` param accuracy→mastery, prompt + cache-key reworded.
- [x] **Fix 4 — Question progress cache bust** — `routers/questions.py` busts `roadmap:{uid}` after commit.

## 🟢 End-to-end verification (step6 Part B)
- [ ] Run backend + frontend against live env with a dev JWT for `shnavii11`; walk every page
  (Dashboard, Questions, Roadmap, Sheet, Profile own + `/profile/<other>`).
- [ ] Regression-check Fix 2 (sheet done → Dashboard updates immediately) and Fix 4 (question done →
  Roadmap updates immediately).
- [ ] Browser-confirm the Insights fix renders in the actual Dashboard UI (API already verified PASS).
- [ ] Once Gemini quota/key is set, exercise the 3 `/insights/*` endpoints against the real provider.

## 🔵 Backlog (larger, recorded only)
- [ ] **Deployment** — Vercel (frontend) + Railway (backend) + Supabase (DB).
- [ ] **Thicken curated sheet** 250 → 350–450 problems (only 2 of 16 sheet sources currently resolve).
- [ ] Investigate odd weakness bands (e.g. `arrays` at 174 solved still flags "high-priority" in the
  explain fallback — check stored `weakness_score` for high-volume topics).
- [ ] Minor hardening: `llm.py` groq branch uses `gemini_api_key` for its auth header; recommend
  cache key truncates `solved_ids[:20]`; unused `@vitest/ui` devDep.

## ✅ Done this session (for context, not remaining)
- Insights resilience fix (stop caching empty LLM results; corpus + deterministic fallbacks for
  recommendations / topic-explain / readiness-summary). Committed `92cc6a9`, pushed, API-verified PASS.
- Repaired `backend/.venv` (3.9.6 symlinks + `pyvenv.cfg`) and the broken `uvicorn`/`pytest` console
  scripts after an accidental 3.14 venv-recreate. 21 backend tests green.
