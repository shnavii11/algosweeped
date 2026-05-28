"""Runtime LeetCode user stats fetcher (for /stats/sync)."""
import httpx
from ..cache import get_cached, set_cached
from ..config import get_settings

GRAPHQL = "https://leetcode.com/graphql"

USER_QUERY = """
query userStats($username: String!) {
  matchedUser(username: $username) {
    submitStatsGlobal {
      acSubmissionNum { difficulty count }
    }
    tagProblemCounts {
      advanced { tagName tagSlug problemsSolved }
      intermediate { tagName tagSlug problemsSolved }
      fundamental { tagName tagSlug problemsSolved }
    }
    profile { ranking reputation }
  }
}
"""

RECENT_QUERY = """
query recentSubmissions($username: String!) {
  recentSubmissionList(username: $username, limit: 20) {
    title titleSlug timestamp statusDisplay lang
  }
}
"""


async def fetch_user(username: str) -> dict:
    cache_key = f"lc:{username}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    s = get_settings()
    headers = {
        "Referer": "https://leetcode.com",
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json",
    }
    if s.leetcode_session:
        headers["Cookie"] = f"LEETCODE_SESSION={s.leetcode_session}; csrftoken={s.leetcode_csrf_token}"

    async with httpx.AsyncClient(headers=headers, timeout=15) as client:
        stats_resp = await client.post(GRAPHQL, json={"query": USER_QUERY, "variables": {"username": username}})
        stats_data = stats_resp.json().get("data", {}).get("matchedUser") or {}

        recent_resp = await client.post(GRAPHQL, json={"query": RECENT_QUERY, "variables": {"username": username}})
        recent = recent_resp.json().get("data", {}).get("recentSubmissionList") or []

    result = {**stats_data, "recentSubmissions": recent}
    await set_cached(cache_key, result, ttl=21600)
    return result
