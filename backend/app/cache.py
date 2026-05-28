import json
import hashlib
from typing import Any, Optional

import redis.asyncio as aioredis
from .config import get_settings

_client: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        url = get_settings().redis_url
        if url:
            _client = aioredis.from_url(url, decode_responses=True)
    return _client


async def get_cached(key: str) -> Optional[Any]:
    r = get_redis()
    if not r:
        return None
    try:
        data = await r.get(key)
        return json.loads(data) if data else None
    except Exception:
        return None


async def set_cached(key: str, value: Any, ttl: int = 21600) -> None:
    r = get_redis()
    if not r:
        return
    try:
        await r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


async def delete_cached(key: str) -> None:
    r = get_redis()
    if not r:
        return
    try:
        await r.delete(key)
    except Exception:
        pass


def cache_key_for_input(prefix: str, payload: dict) -> str:
    h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return f"{prefix}:{h}"
