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

_BREAKDOWN_LABELS = {
    "dsa_consistency": "DSA consistency",
    "github_activity": "GitHub activity",
    "topic_coverage": "topic coverage",
    "sheet_progress": "sheet progress",
}


def _fallback_readiness_summary(total: float, breakdown: dict) -> str:
    """Deterministic narrative when the LLM is unavailable (e.g. quota 429)."""
    if not breakdown:
        return f"Your interview readiness is {total}/100. Keep grinding the weak topics below."
    items = sorted(breakdown.items(), key=lambda kv: kv[1])
    weakest = _BREAKDOWN_LABELS.get(items[0][0], items[0][0])
    strongest = _BREAKDOWN_LABELS.get(items[-1][0], items[-1][0])
    return (
        f"Your interview readiness is {total}/100 — strongest in {strongest} and weakest "
        f"in {weakest}. Focus on raising {weakest} to move the score up."
    )


def _fallback_topic_explanation(topic, solved, weakness, summary, core_patterns) -> str:
    """Deterministic topic-gap diagnosis when the LLM is unavailable."""
    name = topic.replace("-", " ")
    w = weakness or 0.0
    if w > 0.7:
        band = f"This is a high-priority gap — you've solved only {solved} {name} problems."
    elif w > 0.4:
        band = f"You're developing in {name} ({solved} solved), but it's not yet interview-solid."
    else:
        band = f"You're fairly solid in {name} ({solved} solved); keep it warm."
    pieces = [band]
    if summary:
        pieces.append(summary)
    if core_patterns:
        pieces.append("Drill these patterns next: " + ", ".join(list(core_patterns)[:4]) + ".")
    return " ".join(pieces)


@router.get("/readiness-summary")
async def readiness_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    score = await compute_readiness_for_user(current_user, db)
    summary = await llm.summarize_readiness(score["breakdown"])
    if not summary:
        summary = _fallback_readiness_summary(score["total"], score["breakdown"])
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

    # The LLM can be rate-limited (429) or return slugs absent from the corpus, leaving
    # `resolved` short. Top up with real corpus problems in the user's weak topics so the
    # recommendations card is never empty.
    if len(resolved) < 3 and weak_topics:
        exclude = list(solved_ids | {r["id"] for r in resolved}) or [""]
        fb = await db.execute(text("""
            SELECT DISTINCT q.id, q.title, q.slug, q.url, q.difficulty, q.platform,
                   q.acceptance_rate
            FROM questions q
            JOIN question_topics qt ON qt.question_id = q.id
            WHERE qt.topic = ANY(:topics)
              AND COALESCE(q.is_premium, false) = false
              AND NOT (q.id = ANY(:exclude))
            ORDER BY q.acceptance_rate DESC NULLS LAST
            LIMIT :lim
        """), {"topics": weak_topics, "exclude": exclude, "lim": 3 - len(resolved)})
        for r in fb:
            row = dict(r._mapping)
            row.pop("acceptance_rate", None)
            resolved.append(row)

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

    # accuracy is meaningless (attempted == solved placeholder), so derive a
    # mastery proxy from weakness_score instead: mastery = 1 - weakness (HIGHER
    # weakness = WEAKER), clamped via the score's [0,1] range.
    mastery = round(1.0 - (ts.weakness_score or 0.0), 2)
    explanation = await llm.explain_topic_gap(topic, mastery, ts.solved)
    if not explanation:
        rm = await db.execute(
            text("SELECT summary, core_patterns FROM roadmap_topics WHERE topic = :t"),
            {"t": topic},
        )
        rm_row = rm.mappings().first()
        explanation = _fallback_topic_explanation(
            topic,
            ts.solved,
            ts.weakness_score,
            rm_row["summary"] if rm_row else None,
            rm_row["core_patterns"] if rm_row else None,
        )
    return {"success": True, "data": {"topic": topic, "explanation": explanation}}
