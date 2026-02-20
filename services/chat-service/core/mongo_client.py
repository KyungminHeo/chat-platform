from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings

client = AsyncIOMotorClient(settings.MONGO_URL)
db = client[settings.MONGO_DB]

# 컬렉션 (RDB의 테이블 개념)
message_collection = db["messages"]
room_collection = db["rooms"]

async def init_indexes():
    # 자주 조회되는 필드에 인덱스 생성
    await message_collection.create_index("room_id")           # 채팅방별 메시지 조회
    await message_collection.create_index("created_at")        # 시간순 정렬
    await message_collection.create_index([
        ("room_id", 1), ("created_at", -1)                     # 복합 인덱스 (가장 많이 쓰는 쿼리)
    ])