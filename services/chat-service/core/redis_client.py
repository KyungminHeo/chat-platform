import redis.asyncio as redis
from core.config import settings

redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    max_connections=100,
)

async def get_redis():
    return redis_client