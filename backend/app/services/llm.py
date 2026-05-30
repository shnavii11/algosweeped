"""
Narrow LLM client — three bounded functions, no free-form chat.
Default: Gemini 2.0 Flash via Google AI Studio free tier.
Pluggable: LLM_PROVIDER=groq|mistral to swap.
Every call cached in Redis by sha256(inputs) with 24h TTL.
"""
import json
from typing import Optional
import httpx
from ..config import get_settings
from ..cache import get_cached, set_cached, cache_key_for_input


async def _call_gemini(prompt: str) -> str:
    s = get_settings()
    if not s.gemini_api_key:
        return ""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={s.gemini_api_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=body, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


async def _call_llm(prompt: str) -> str:
    s = get_settings()
    provider = s.llm_provider.lower()
    if provider == "groq":
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json={"model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}]},
                headers={"Authorization": f"Bearer {s.gemini_api_key}"},
                timeout=20,
            )
            return resp.json()["choices"][0]["message"]["content"]
    return await _call_gemini(prompt)


async def recommend_next_problems(weak_topics: list[str], solved_ids: set[str]) -> list[str]:
    key = cache_key_for_input("llm:recommend", {"topics": sorted(weak_topics), "solved": sorted(solved_ids)[:20]})
    cached = await get_cached(key)
    if cached:
        return cached

    prompt = (
        f"You are a DSA coaching system. A student is weak in: {', '.join(weak_topics)}. "
        f"Recommend exactly 3 LeetCode problem slugs (e.g. 'two-sum') that best address these gaps. "
        f"Return only a JSON array of 3 slugs, nothing else."
    )
    try:
        text = await _call_llm(prompt)
        slugs = json.loads(text.strip())
        result = [f"lc-{s}" if not s.startswith("lc-") else s for s in slugs[:3]]
    except Exception:
        result = []

    # Never cache an empty/failed result — a transient 429 or outage would
    # otherwise poison the cache for 24h and keep recommendations blank even
    # after the provider recovers. The router supplies a corpus fallback.
    if result:
        await set_cached(key, result, ttl=86400)
    return result


async def summarize_readiness(score_breakdown: dict) -> str:
    key = cache_key_for_input("llm:readiness", score_breakdown)
    cached = await get_cached(key)
    if cached:
        return cached

    prompt = (
        f"Given this interview readiness score breakdown: {json.dumps(score_breakdown)}, "
        f"write exactly 2 sentences summarizing the student's strengths and what to focus on next. "
        f"Be direct, no filler."
    )
    try:
        text = await _call_llm(prompt)
    except Exception:
        text = ""

    if text:  # don't cache an empty result (see recommend_next_problems)
        await set_cached(key, text, ttl=86400)
    return text


async def explain_topic_gap(topic: str, mastery: float, volume: int) -> str:
    key = cache_key_for_input("llm:gap", {"topic": topic, "mastery": mastery, "volume": volume})
    cached = await get_cached(key)
    if cached:
        return cached

    prompt = (
        f"A student has solved {volume} {topic} problems (≈{mastery*100:.0f}% of a target baseline). "
        f"Write one paragraph (3-4 sentences) diagnosing their gap and the specific sub-pattern they should drill. "
        f"Be concrete, no generic advice."
    )
    try:
        text = await _call_llm(prompt)
    except Exception:
        text = ""

    if text:  # don't cache an empty result (see recommend_next_problems)
        await set_cached(key, text, ttl=86400)
    return text
