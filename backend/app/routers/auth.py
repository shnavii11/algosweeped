"""GitHub OAuth flow + JWT issuance."""
from datetime import datetime, timedelta, timezone
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def create_jwt(user_id: str, username: str) -> str:
    s = get_settings()
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=s.jwt_expire_minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


async def get_github_user(code: str) -> dict:
    s = get_settings()
    async with httpx.AsyncClient() as client:
        # Exchange code for token
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={"client_id": s.github_client_id,
                  "client_secret": s.github_client_secret,
                  "code": code},
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(400, "GitHub OAuth failed")

        # Fetch user profile
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}",
                     "Accept": "application/vnd.github.v3+json"},
        )
        gh_user = user_resp.json()

        # Fetch primary email if not public
        email = gh_user.get("email")
        if not email:
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}",
                         "Accept": "application/vnd.github.v3+json"},
            )
            for e in emails_resp.json():
                if e.get("primary"):
                    email = e["email"]
                    break

        return {**gh_user, "email": email, "_access_token": access_token}


@router.get("/github")
async def github_login():
    s = get_settings()
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={s.github_client_id}"
        f"&scope=user:email,read:user"
    )
    return RedirectResponse(url)


@router.get("/github/callback")
async def github_callback(code: str = Query(...), db: AsyncSession = Depends(get_db)):
    gh = await get_github_user(code)
    email = gh.get("email")
    if not email:
        raise HTTPException(400, "Could not retrieve email from GitHub")

    # Upsert user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        username = gh.get("login", email.split("@")[0])
        # Ensure unique username
        existing = await db.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none():
            username = f"{username}_{str(uuid.uuid4())[:6]}"

        user = User(
            email=email,
            name=gh.get("name") or gh.get("login"),
            username=username,
            avatar_url=gh.get("avatar_url"),
            github_login=gh.get("login"),
            gh_username=gh.get("login"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.avatar_url = gh.get("avatar_url") or user.avatar_url
        user.github_login = gh.get("login") or user.github_login
        await db.commit()

    token = create_jwt(str(user.id), user.username)
    s = get_settings()
    is_new = user.lc_username is None and user.cf_handle is None
    redirect = f"{s.frontend_url}/login?token={token}&new={'1' if is_new else '0'}"
    return RedirectResponse(redirect)


@router.post("/refresh")
async def refresh_token(token: str, db: AsyncSession = Depends(get_db)):
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=["HS256"],
                             options={"verify_exp": False})
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(401, "Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    new_token = create_jwt(str(user.id), user.username)
    return {"success": True, "data": {"access_token": new_token}}
