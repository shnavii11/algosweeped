from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..models.question import SheetProgress
from ..cache import get_cached, set_cached, delete_cached
from .deps import get_current_user

router = APIRouter(prefix="/sheet", tags=["sheet"])


@router.get("/curated")
async def get_curated_sheet(db: AsyncSession = Depends(get_db)):
    cached = await get_cached("sheet:curated")
    if cached:
        return {"success": True, "data": cached, "meta": {"cached": True}}

    sql = text("""
        SELECT csp.question_id, csp.topic, csp.ordinal, csp.cross_sheet_count,
               csp.source_sheets, csp.score,
               q.title, q.url, q.difficulty, q.platform, q.slug, q.is_premium
        FROM curated_sheet_problems csp
        JOIN questions q ON q.id = csp.question_id
        WHERE csp.sheet_id = 'optimal_mix_v1'
        ORDER BY csp.topic, csp.ordinal
    """)
    result = await db.execute(sql)
    rows = [dict(r._mapping) for r in result]

    # Group by topic
    grouped: dict = {}
    for r in rows:
        t = r["topic"]
        grouped.setdefault(t, [])
        grouped[t].append(r)

    await set_cached("sheet:curated", grouped, ttl=86400)
    return {"success": True, "data": grouped, "meta": {"cached": False, "total": len(rows)}}


@router.get("/sources")
async def get_sheet_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM sheet_sources ORDER BY weight DESC"))
    rows = [dict(r._mapping) for r in result]
    return {"success": True, "data": rows}


@router.get("/progress/me")
async def get_my_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SheetProgress).where(SheetProgress.user_id == current_user.id)
    )
    progs = result.scalars().all()
    data = {p.problem_id: p.status for p in progs}
    total = await db.execute(
        text("SELECT count(*) FROM curated_sheet_problems WHERE sheet_id='optimal_mix_v1'")
    )
    total_count = total.scalar()
    done_count = sum(1 for v in data.values() if v == "done")
    return {
        "success": True,
        "data": {
            "progress_map": data,
            "done": done_count,
            "total": total_count,
            "pct": round(done_count / max(total_count, 1) * 100, 1),
        },
    }


@router.patch("/progress/{problem_id}")
async def update_sheet_progress(
    problem_id: str,
    status: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SheetProgress).where(
            SheetProgress.user_id == current_user.id,
            SheetProgress.problem_id == problem_id,
        )
    )
    prog = result.scalar_one_or_none()
    if prog:
        prog.status = status
    else:
        prog = SheetProgress(user_id=current_user.id, problem_id=problem_id, status=status)
        db.add(prog)
    await db.commit()
    # Sheet progress feeds stats (sheet.done/total, 1h) and readiness (reads
    # sheet_progress, 1h) — bust both so the Dashboard reflects the change now.
    await delete_cached(f"stats:{current_user.id}")
    await delete_cached(f"readiness:{current_user.id}")
    return {"success": True, "data": {"status": status}}
