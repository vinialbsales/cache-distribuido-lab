from collections.abc import AsyncGenerator

from fastapi import Request
from redis.asyncio import Redis, from_url

from app.core.config import get_settings


def create_redis_client() -> Redis:
    settings = get_settings()
    return from_url(settings.redis_url, decode_responses=True)


async def get_redis(request: Request) -> AsyncGenerator[Redis, None]:
    yield request.app.state.redis
