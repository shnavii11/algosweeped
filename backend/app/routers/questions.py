from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.question import Question, QuestionTopic, QuestionProgress
from ..models.user import User
from ..schemas.question import QuestionOut, QuestionProgressUpdate
from ..cache import get_cached, set_cached, delete_cached
from .deps import get_current_user

router = APIRouter(prefix="/questions", tags=["questions"])


def _q_url_args(topic, platform, difficulty, company, q):
    return f"{topic}|{platform}|{difficulty}|{company}|{q}"


@router.get("")
async def list_questions(
    topic: Optional[str] = None,
    platform: Optional[str] = None,
    difficulty: Optional[str] = None,
    company: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"questions:{_q_url_args(topic,platform,difficulty,company,q)}:{skip}:{limit}"
    cached = await get_cached(cache_key)
    if cached:
        return {"success": True, "data": cached, "meta": {"cached": True}}

    sql = """
        SELECT q.id, q.platform, q.number, q.title, q.slug, q.url,
               q.difficulty, q.difficulty_rating, q.is_premium,
               q.acceptance_rate, q.solved_count,
               ARRAY_AGG(DISTINCT qt.topic) FILTER (WHERE qt.topic IS NOT NULL) AS topics,
               ARRAY_AGG(DISTINCT qc.company) FILTER (WHERE qc.company IS NOT NULL) AS companies
        FROM questions q
        LEFT JOIN question_topics qt ON qt.question_id = q.id
        LEFT JOIN question_companies qc ON qc.question_id = q.id
        WHERE 1=1
    """
    params: dict = {}
    if topic:
        sql += " AND EXISTS (SELECT 1 FROM question_topics WHERE question_id=q.id AND topic=:topic)"
        params["topic"] = topic
    if platform:
        sql += " AND q.platform = :platform"
        params["platform"] = platform
    if difficulty:
        sql += " AND q.difficulty = :difficulty"
        params["difficulty"] = difficulty
    if company:
        sql += " AND EXISTS (SELECT 1 FROM question_companies WHERE question_id=q.id AND company ILIKE :company)"
        params["company"] = f"%{company}%"
    if q:
        sql += " AND q.title ILIKE :q"
        params["q"] = f"%{q}%"
    sql += " GROUP BY q.id ORDER BY q.platform, q.id LIMIT :limit OFFSET :skip"
    params["limit"] = limit
    params["skip"] = skip

    result = await db.execute(text(sql), params)
    rows = [dict(r._mapping) for r in result]

    await set_cached(cache_key, rows, ttl=43200)
    return {"success": True, "data": rows, "meta": {"cached": False, "count": len(rows)}}


@router.get("/by-topic")
async def questions_by_topic(db: AsyncSession = Depends(get_db)):
    cached = await get_cached("qtopics:all")
    if cached:
        return {"success": True, "data": cached, "meta": {"cached": True}}

    # Top 100 per topic: LC questions ranked by company mentions + acceptance rate
    sql = text("""
        WITH ranked AS (
            SELECT
                qt.topic,
                q.id, q.platform, q.number, q.title, q.slug, q.url,
                q.difficulty, q.is_premium, q.acceptance_rate,
                (SELECT COUNT(*) FROM question_companies qc WHERE qc.question_id = q.id) AS company_count,
                ROW_NUMBER() OVER (
                    PARTITION BY qt.topic
                    ORDER BY q.platform,
                             (SELECT COUNT(*) FROM question_companies qc WHERE qc.question_id = q.id) DESC,
                             COALESCE(q.acceptance_rate, 0) DESC
                ) AS rn
            FROM question_topics qt
            JOIN questions q ON q.id = qt.question_id
            WHERE q.is_premium = false
        )
        SELECT topic, id, platform, number, title, slug, url,
               difficulty, is_premium, acceptance_rate, company_count
        FROM ranked
        WHERE rn <= 100
        ORDER BY topic, platform, company_count DESC
    """)
    result = await db.execute(sql)
    rows = result.mappings().all()

    grouped: dict = {}
    for r in rows:
        t = r["topic"]
        grouped.setdefault(t, [])
        grouped[t].append(dict(r))

    await set_cached("qtopics:all", grouped, ttl=43200)
    return {"success": True, "data": grouped, "meta": {"cached": False}}


@router.get("/{question_id}")
async def get_question(question_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if not q:
        from fastapi import HTTPException
        raise HTTPException(404, "Question not found")

    topics_res = await db.execute(select(QuestionTopic).where(QuestionTopic.question_id == question_id))
    topics = [r.topic for r in topics_res.scalars()]

    return {"success": True, "data": {**q.__dict__, "topics": topics}}


@router.patch("/{question_id}/progress")
async def update_progress(
    question_id: str,
    body: QuestionProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QuestionProgress).where(
            QuestionProgress.user_id == current_user.id,
            QuestionProgress.question_id == question_id,
        )
    )
    prog = result.scalar_one_or_none()
    if prog:
        prog.status = body.status
        if body.notes is not None:
            prog.notes = body.notes
    else:
        prog = QuestionProgress(
            user_id=current_user.id,
            question_id=question_id,
            status=body.status,
            notes=body.notes,
        )
        db.add(prog)
    await db.commit()
    # Roadmap derives per-topic user_solved/user_attempted from question_progress
    # and caches it (roadmap:{uid}, 1h) — bust it so the Roadmap page updates now.
    # stats:/readiness: are NOT fed by question_progress, so leave them alone.
    await delete_cached(f"roadmap:{current_user.id}")
    return {"success": True, "data": {"status": body.status}}
