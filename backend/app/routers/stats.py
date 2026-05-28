"""Aggregate stats, sync, readiness score."""
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User, PlatformSnapshot, TopicScore
from ..cache import get_cached, set_cached, delete_cached
from ..services.intelligence import compute_weakness_score, compute_readiness_score, normalize_lc_topic
from .deps import get_current_user

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/me")
async def get_my_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"stats:{current_user.id}"
    cached = await get_cached(cache_key)
    if cached:
        return {"success": True, "data": cached, "meta": {"cached": True}}

    # Latest snapshot per platform
    snapshots = {}
    for platform in ("leetcode", "codeforces", "github"):
        result = await db.execute(text("""
            SELECT raw_data, fetched_at FROM platform_snapshots
            WHERE user_id=:uid AND platform=:p
            ORDER BY fetched_at DESC LIMIT 1
        """), {"uid": str(current_user.id), "p": platform})
        row = result.first()
        if row:
            snapshots[platform] = {"data": row.raw_data, "fetched_at": row.fetched_at.isoformat()}

    # Topic scores
    ts_result = await db.execute(
        select(TopicScore).where(TopicScore.user_id == current_user.id)
    )
    topic_scores = [
        {"topic": ts.topic, "solved": ts.solved, "attempted": ts.attempted,
         "accuracy": ts.accuracy, "weakness_score": ts.weakness_score}
        for ts in ts_result.scalars()
    ]

    # Sheet progress
    sheet_res = await db.execute(text("""
        SELECT count(*) FILTER (WHERE status='done') AS done,
               count(*) AS total
        FROM sheet_progress WHERE user_id=:uid
    """), {"uid": str(current_user.id)})
    sheet_row = sheet_res.first()
    sheet_done = int(sheet_row.done or 0)
    sheet_total = int(sheet_row.total or 0)

    data = {
        "user": {"username": current_user.username, "last_synced": current_user.last_synced.isoformat() if current_user.last_synced else None},
        "snapshots": snapshots,
        "topic_scores": topic_scores,
        "sheet": {"done": sheet_done, "total": sheet_total},
    }
    await set_cached(cache_key, data, ttl=3600)
    return {"success": True, "data": data, "meta": {"cached": False}}


@router.post("/sync")
async def sync_platforms(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    background_tasks.add_task(_do_sync, str(current_user.id))
    return {"success": True, "data": {"message": "Sync started in background"}}


async def _do_sync(user_id: str):
    """Background task: fetch from all platforms, compute scores, update DB."""
    from ..database import AsyncSessionLocal
    from ..services import leetcode as lc_svc, codeforces as cf_svc, github as gh_svc

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        for platform, username_attr, fetch_fn in [
            ("leetcode", "lc_username", lc_svc.fetch_user),
            ("codeforces", "cf_handle", cf_svc.fetch_user),
            ("github", "gh_username", gh_svc.fetch_user),
        ]:
            username = getattr(user, username_attr)
            if not username:
                continue
            try:
                data = await fetch_fn(username)
                snap = PlatformSnapshot(user_id=user.id, platform=platform, raw_data=data)
                db.add(snap)
                await db.flush()
            except Exception as e:
                print(f"[sync] {platform} failed for {user_id}: {e}")

        # Recompute topic scores from latest LC snapshot
        lc_snap = await db.execute(text("""
            SELECT raw_data FROM platform_snapshots
            WHERE user_id=:uid AND platform='leetcode'
            ORDER BY fetched_at DESC LIMIT 1
        """), {"uid": user_id})
        lc_row = lc_snap.first()
        if lc_row:
            # Aggregate solved counts by canonical topic (many raw LC tag-slugs
            # collapse onto one canonical topic, e.g. tree/binary-tree/dfs/bfs → trees).
            tag_counts = lc_row.raw_data.get("tagProblemCounts", {})
            agg: dict[str, int] = {}
            for difficulty_group in tag_counts.values():
                for tag_data in difficulty_group:
                    canon = normalize_lc_topic(tag_data.get("tagSlug", ""))
                    if canon is None:
                        continue
                    agg[canon] = agg.get(canon, 0) + tag_data.get("problemsSolved", 0)

            # Clear stale rows (including legacy raw-slug rows) so canonical scores
            # don't coexist with old data, then insert one fresh row per topic.
            await db.execute(
                text("DELETE FROM topic_scores WHERE user_id = :uid"), {"uid": user_id}
            )
            for canon, solved in agg.items():
                db.add(TopicScore(
                    user_id=user_id, topic=canon, solved=solved, attempted=solved,
                    weakness_score=compute_weakness_score(canon, solved, solved),
                ))

        user.last_synced = datetime.now(timezone.utc)
        await db.commit()
        await delete_cached(f"stats:{user_id}")
        await delete_cached(f"roadmap:{user_id}")


@router.get("/{username}/readiness")
async def get_readiness(username: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    cache_key = f"readiness:{user.id}"
    cached = await get_cached(cache_key)
    if cached:
        return {"success": True, "data": cached, "meta": {"cached": True}}

    # Pull latest snapshot stats
    lc_snap = await db.execute(text("""
        SELECT raw_data FROM platform_snapshots
        WHERE user_id=:uid AND platform='leetcode' ORDER BY fetched_at DESC LIMIT 1
    """), {"uid": str(user.id)})
    lc_row = lc_snap.first()
    lc_data = lc_row.raw_data if lc_row else {}

    cf_snap = await db.execute(text("""
        SELECT raw_data FROM platform_snapshots
        WHERE user_id=:uid AND platform='codeforces' ORDER BY fetched_at DESC LIMIT 1
    """), {"uid": str(user.id)})
    cf_row = cf_snap.first()
    cf_data = cf_row.raw_data if cf_row else {}

    gh_snap = await db.execute(text("""
        SELECT raw_data FROM platform_snapshots
        WHERE user_id=:uid AND platform='github' ORDER BY fetched_at DESC LIMIT 1
    """), {"uid": str(user.id)})
    gh_row = gh_snap.first()
    gh_data = gh_row.raw_data if gh_row else {}

    ts_result = await db.execute(
        select(TopicScore).where(TopicScore.user_id == user.id)
    )
    topic_scores = [{"topic": ts.topic, "weakness_score": ts.weakness_score} for ts in ts_result.scalars()]

    sheet_res = await db.execute(text("""
        SELECT count(*) FILTER (WHERE status='done') AS done, count(*) AS total
        FROM sheet_progress WHERE user_id=:uid
    """), {"uid": str(user.id)})
    sr = sheet_res.first()

    # Extract counts from raw snapshots
    lc_counts = lc_data.get("submitStatsGlobal", {}).get("acSubmissionNum", [])
    lc_by_diff = {d["difficulty"]: d["count"] for d in lc_counts}

    score = compute_readiness_score(
        lc_easy=lc_by_diff.get("Easy", 0),
        lc_medium=lc_by_diff.get("Medium", 0),
        lc_hard=lc_by_diff.get("Hard", 0),
        cf_solved=cf_data.get("problemsSolved", 0),
        github_active_repos=len([r for r in gh_data.get("repos", []) if r.get("recent_commit")]),
        topic_scores=topic_scores,
        sheet_done=int(sr.done or 0),
        sheet_total=int(sr.total or 1),
    )

    await set_cached(cache_key, score, ttl=3600)
    return {"success": True, "data": score, "meta": {"cached": False}}


@router.get("/{username}/topics")
async def get_topics(username: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    ts_result = await db.execute(
        select(TopicScore).where(TopicScore.user_id == user.id)
    )
    rows = [
        {"topic": ts.topic, "solved": ts.solved, "attempted": ts.attempted,
         "accuracy": ts.accuracy, "weakness_score": ts.weakness_score}
        for ts in ts_result.scalars()
    ]
    rows.sort(key=lambda x: x.get("weakness_score") or 1.0)
    return {"success": True, "data": rows}
