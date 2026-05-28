"""Idempotent upsert helpers for each corpus table."""
import json
import asyncpg


def _j(v):
    """Serialize a value to JSON string for asyncpg JSONB parameters."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    return json.dumps(v)


async def upsert_question(conn: asyncpg.Connection, q: dict):
    await conn.execute("""
        INSERT INTO questions
          (id, platform, number, title, slug, url, difficulty, difficulty_rating,
           statement_html, statement_text, constraints, examples, hints,
           is_premium, acceptance_rate, solved_count, raw, fetched_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,now())
        ON CONFLICT (id) DO UPDATE SET
          title            = EXCLUDED.title,
          difficulty       = EXCLUDED.difficulty,
          difficulty_rating= EXCLUDED.difficulty_rating,
          statement_html   = COALESCE(EXCLUDED.statement_html, questions.statement_html),
          statement_text   = COALESCE(EXCLUDED.statement_text, questions.statement_text),
          constraints      = COALESCE(EXCLUDED.constraints,    questions.constraints),
          examples         = COALESCE(EXCLUDED.examples,       questions.examples),
          hints            = COALESCE(EXCLUDED.hints,          questions.hints),
          is_premium       = EXCLUDED.is_premium,
          acceptance_rate  = COALESCE(EXCLUDED.acceptance_rate,questions.acceptance_rate),
          solved_count     = COALESCE(EXCLUDED.solved_count,   questions.solved_count),
          raw              = EXCLUDED.raw,
          fetched_at       = now()
    """,
        q["id"], q["platform"], q.get("number"), q["title"], q.get("slug"),
        q["url"], q.get("difficulty"), q.get("difficulty_rating"),
        q.get("statement_html"), q.get("statement_text"),
        _j(q.get("constraints")), _j(q.get("examples")), _j(q.get("hints")),
        q.get("is_premium", False), q.get("acceptance_rate"), q.get("solved_count"),
        _j(q.get("raw")),
    )


async def upsert_question_topics(conn: asyncpg.Connection, question_id: str, topics: list[str]):
    for topic in topics:
        await conn.execute("""
            INSERT INTO question_topics (question_id, topic)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
        """, question_id, topic)


async def upsert_question_companies(conn: asyncpg.Connection, question_id: str, companies: list[dict]):
    for c in companies:
        await conn.execute("""
            INSERT INTO question_companies (question_id, company, frequency, timeframe)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (question_id, company, timeframe) DO UPDATE SET
              frequency = EXCLUDED.frequency
        """, question_id, c["name"], c.get("frequency"), c.get("timeframe", "all"))


async def upsert_fetch_run(conn: asyncpg.Connection, platform: str, layer: str,
                            status: str, count: int, notes: str = "", errors: list = None):
    import json
    await conn.execute("""
        INSERT INTO fetch_runs (platform, layer, status, problem_count, notes, errors, finished_at)
        VALUES ($1, $2, $3, $4, $5, $6, now())
    """, platform, layer, status, count, notes,
        json.dumps(errors) if errors else None)
