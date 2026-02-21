from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text

from core.database import engine, Base
from core.redis_client import redis_client
from routers.user_router import router as user_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시
    print("Starting user-service...")

    # DB 테이블 자동 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # DB 연결 확인
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    print("PostgreSQL connected")

    # Redis 연결 확인
    await redis_client.ping()
    print("Redis connected")

    yield  # 앱 실행 중

    # 앱 종료 시
    await engine.dispose()
    await redis_client.aclose()
    print("Connections closed")

app = FastAPI(
    title="User Service",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS는 Nginx 게이트웨이에서 처리 (중복 설정 방지)

app.include_router(user_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
