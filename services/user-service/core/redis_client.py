import redis.asyncio as redis
from core.config import settings

# 앱 시작 시 한 번만 생성 - 커넥션 풀 자동 관리
redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,  # bytes 대신 str로 자동 변환
    max_connections=100,
)

async def get_redis():
    return redis_client