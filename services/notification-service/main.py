from contextlib import asynccontextmanager
from fastapi import FastAPI
import asyncio

from core.redis_client import redis_client
from consumers.message_consumer import consume
from routers.notify_router import router as notify_router

consumer_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer_task
    
    print("Starting notification-service...")
    
    await redis_client.ping()
    print("Redis connected")
    
    # Kafka Consumer를 백그라운드 태스크로 실행
    consumer_task = asyncio.create_task(consume())
    print("Kafka Consumer task started")

    # 앱 실행 중
    yield
    
    # 종료 시
    if consumer_task:
        consumer_task.cancel()
        await asyncio.gather(consumer_task, return_exceptions=True)
        
    await redis_client.aclose()
    print("Connections closed")
    
app = FastAPI(
    title="Notification Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(notify_router)

@app.get("/health")
async def health():
    return {"status": "ok"}