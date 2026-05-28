"""LLM-backed insights: readiness narrative, problem recommendations, topic-gap explanations.

Each endpoint wraps one of the three bounded functions in services/llm.py (all
Redis-cached 24h by input hash). The LLM functions degrade gracefully (return
""/[] on error), so these endpoints stay 200 even when the provider is down or
rate-limited.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User, TopicScore
from ..services import llm
from .deps import get_current_user
from .stats import compute_readiness_for_user

router = APIRouter(prefix="/insights", tags=["insights"])

WEAK_TOPIC_LIMIT = 4


@router.get("/readiness-summary")
async def readiness_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    score = await compute_readiness_for_user(current_user, db)
    summary = await llm.summarize_readiness(score["breakdown"])
    return {
        "success": True,
        "data": {"summary": summary, "total": score["total"], "breakdown": score["breakdown"]},
    }


@router.get("/recommendations")
async def recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Weakest topics first (highest weakness_score = important + under-solved).
    ts_result = await db.execute(
        select(TopicScore.topic)
        .where(TopicScore.user_id == current_user.id)
        .order_by(TopicScore.weakness_score.desc())
        .limit(WEAK_TOPIC_LIMIT)
    )
    weak_topics = [row[0] for row in ts_result.all()]

    # Problems the user has already marked done in either tracker — avoid re-recommending.
    solved_res = await db.execute(text("""
        SELECT question_id AS id FROM question_progress WHERE user_id=:uid AND status='done'
        UNION
        SELECT problem_id AS id FROM sheet_progress WHERE user_id=:uid AND status='done'
    """), {"uid": str(current_user.id)})
    solved_ids = {row.id for row in solved_res}

    rec_ids = await llm.recommend_next_problems(weak_topics, solved_ids)

    # The LLM returns slug-based ids (lc-<slug>); the corpus is keyed by lc-<number>,
    # so resolve against the slug column. Preserve the LLM's ordering.
    slugs = [rid.split("-", 1)[1] for rid in rec_ids if "-" in rid]
    resolved: list[dict] = []
    if slugs:
        rows = await db.execute(text("""
            SELECT id, title, slug, url, difficulty, platform
            FROM questions WHERE slug = ANY(:slugs)
        """), {"slugs": slugs})
        by_slug = {r.slug: dict(r._mapping) for r in rows}
        resolved = [by_slug[s] for s in slugs if s in by_slug]

    return {"success": True, "data": {"recommendations": resolved, "weak_topics": weak_topics}}


@router.get("/topics/{topic}/explain")
async def explain_topic(
    topic: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TopicScore).where(
            TopicScore.user_id == current_user.id, TopicScore.topic == topic
        )
    )
    ts = result.scalar_one_or_none()
    if not ts:
        raise HTTPException(404, "No score for that topic — sync first")

    accuracy = ts.accuracy if ts.accuracy is not None else ts.solved / max(ts.attempted, 1)
    explanation = await llm.explain_topic_gap(topic, accuracy, ts.solved)
    return {"success": True, "data": {"topic": topic, "explanation": explanation}}
