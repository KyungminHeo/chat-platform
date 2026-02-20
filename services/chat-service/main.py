from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.mongo_client import init_indexes
from core.redis_client import redis_client
from core.kafka_client import start_producer, stop_producer
from routers.chat_router import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시
    print("Starting chat-service...")

    # MongoDB 초기화
    await init_indexes()
    print("MongoDB indexes created")

    # Redis 연결 확인
    await redis_client.ping()
    print("Redis connected")

    # Kafka 시작
    await start_producer()

    yield  # 앱 실행 중

    # 종료 시
    await stop_producer()
    await redis_client.aclose()
    print("Connections closed")


app = FastAPI(
    title="Chat Service",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 설정 — 프론트엔드 개발 서버 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
