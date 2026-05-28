"""Per-platform fetch endpoints (triggered by frontend for display)."""
from fastapi import APIRouter, Depends, HTTPException

from ..models.user import User
from ..services import leetcode as lc_svc, codeforces as cf_svc, github as gh_svc
from .deps import get_current_user

router = APIRouter(prefix="/platforms", tags=["platforms"])


@router.get("/leetcode")
async def get_lc(current_user: User = Depends(get_current_user)):
    if not current_user.lc_username:
        raise HTTPException(400, "LeetCode username not set")
    data = await lc_svc.fetch_user(current_user.lc_username)
    return {"success": True, "data": data}


@router.get("/codeforces")
async def get_cf(current_user: User = Depends(get_current_user)):
    if not current_user.cf_handle:
        raise HTTPException(400, "Codeforces handle not set")
    data = await cf_svc.fetch_user(current_user.cf_handle)
    return {"success": True, "data": data}


@router.get("/github")
async def get_gh(current_user: User = Depends(get_current_user)):
    if not current_user.gh_username:
        raise HTTPException(400, "GitHub username not set")
    data = await gh_svc.fetch_user(current_user.gh_username)
    return {"success": True, "data": data}
