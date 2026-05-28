from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..cache import get_cached, set_cached
from .deps import get_current_user

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


@router.get("")
async def get_roadmap(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cache_key = f"roadmap:{current_user.id}"
    cached = await get_cached(cache_key)
    if cached:
        return {"success": True, "data": cached, "meta": {"cached": True}}

    topics_res = await db.execute(
        text("SELECT * FROM roadmap_topics ORDER BY ordinal")
    )
    topics = [dict(r._mapping) for r in topics_res]

    # Attach per-topic progress from user's question_progress
    progress_res = await db.execute(text("""
        SELECT qt.topic,
               COUNT(*) FILTER (WHERE qp.status='done') AS solved,
               COUNT(*) FILTER (WHERE qp.status IN ('attempted','done')) AS attempted
        FROM question_topics qt
        JOIN question_progress qp ON qp.question_id = qt.question_id
        WHERE qp.user_id = :uid
        GROUP BY qt.topic
    """), {"uid": str(current_user.id)})
    prog_map = {r.topic: {"solved": r.solved, "attempted": r.attempted} for r in progress_res}

    # Attach weakness scores
    scores_res = await db.execute(text("""
        SELECT topic, weakness_score FROM topic_scores WHERE user_id=:uid
    """), {"uid": str(current_user.id)})
    score_map = {r.topic: r.weakness_score for r in scores_res}

    for t in topics:
        prog = prog_map.get(t["topic"], {})
        t["user_solved"] = int(prog.get("solved") or 0)
        t["user_attempted"] = int(prog.get("attempted") or 0)
        t["weakness_score"] = score_map.get(t["topic"])

    await set_cached(cache_key, topics, ttl=3600)
    return {"success": True, "data": topics, "meta": {"cached": False}}
