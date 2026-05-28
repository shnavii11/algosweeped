"""Runtime GitHub user stats fetcher."""
from datetime import datetime, timezone, timedelta
import httpx
from ..cache import get_cached, set_cached
from ..config import get_settings

GH_API = "https://api.github.com"


def _headers():
    s = get_settings()
    h = {"Accept": "application/vnd.github.v3+json",
         "User-Agent": "icode-plus/1.0"}
    if s.github_token:
        h["Authorization"] = f"Bearer {s.github_token}"
    return h


async def fetch_user(username: str) -> dict:
    cache_key = f"gh:{username}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    async with httpx.AsyncClient(headers=_headers(), timeout=15) as client:
        profile_resp = await client.get(f"{GH_API}/users/{username}")
        profile = profile_resp.json()

        repos_resp = await client.get(
            f"{GH_API}/users/{username}/repos",
            params={"sort": "updated", "per_page": 30},
        )
        repos = repos_resp.json() if isinstance(repos_resp.json(), list) else []

        events_resp = await client.get(
            f"{GH_API}/users/{username}/events",
            params={"per_page": 100},
        )
        events = events_resp.json() if isinstance(events_resp.json(), list) else []

    # Mark repos with recent activity (last 90 days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    enriched_repos = []
    for r in repos[:10]:
        pushed = r.get("pushed_at")
        recent = False
        if pushed:
            try:
                recent = datetime.fromisoformat(pushed.replace("Z", "+00:00")) > cutoff
            except Exception:
                pass
        enriched_repos.append({
            "name": r.get("name"),
            "url": r.get("html_url"),
            "description": r.get("description"),
            "language": r.get("language"),
            "stars": r.get("stargazers_count", 0),
            "recent_commit": recent,
        })

    # Count push events in last 90 days
    recent_pushes = sum(
        1 for e in events
        if e.get("type") == "PushEvent"
        and datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")) > cutoff
    )

    result = {
        "login": profile.get("login"),
        "name": profile.get("name"),
        "avatar_url": profile.get("avatar_url"),
        "bio": profile.get("bio"),
        "public_repos": profile.get("public_repos"),
        "followers": profile.get("followers"),
        "html_url": profile.get("html_url"),
        "repos": enriched_repos,
        "recent_push_events": recent_pushes,
    }
    await set_cached(cache_key, result, ttl=21600)
    return result
