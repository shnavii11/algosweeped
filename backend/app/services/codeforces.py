"""Runtime Codeforces user stats fetcher."""
import httpx
from ..cache import get_cached, set_cached

CF_API = "https://codeforces.com/api"


async def fetch_user(handle: str) -> dict:
    cache_key = f"cf:{handle}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    async with httpx.AsyncClient(timeout=15) as client:
        info_resp = await client.get(f"{CF_API}/user.info?handles={handle}")
        info = info_resp.json().get("result", [{}])[0]

        rating_resp = await client.get(f"{CF_API}/user.rating?handle={handle}")
        rating_hist = rating_resp.json().get("result", [])

        status_resp = await client.get(f"{CF_API}/user.status?handle={handle}&count=100")
        submissions = status_resp.json().get("result", [])

    solved = set()
    for sub in submissions:
        if sub.get("verdict") == "OK":
            p = sub.get("problem", {})
            solved.add(f"{p.get('contestId')}{p.get('index')}")

    result = {
        **info,
        "problemsSolved": len(solved),
        "ratingHistory": rating_hist[-10:],
        "recentSubmissions": submissions[:20],
    }
    await set_cached(cache_key, result, ttl=21600)
    return result
