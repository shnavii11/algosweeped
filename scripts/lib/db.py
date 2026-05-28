"""Async SQLAlchemy engine + raw asyncpg connection wired to DATABASE_URL."""
import asyncio
import os
from contextlib import asynccontextmanager

import asyncpg
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../backend/.env"))

# Raw asyncpg URL (strip +asyncpg prefix if present)
_raw_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")


async def get_connection() -> asyncpg.Connection:
    return await asyncpg.connect(_raw_url)


@asynccontextmanager
async def connection():
    conn = await get_connection()
    try:
        yield conn
    finally:
        await conn.close()


async def fetchall(sql: str, *args):
    async with connection() as conn:
        return await conn.fetch(sql, *args)


async def execute(sql: str, *args):
    async with connection() as conn:
        return await conn.execute(sql, *args)
