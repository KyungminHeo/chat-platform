from motor.motor_asyncio import AsyncIOMotorCollection
from models.message import Message
from datetime import datetime
from bson import ObjectId

class MessageRepository:
    
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
    
    async def save(self, message: Message) -> Message:
        doc = message.model_dump(exclude={"id"})
        result = await self.collection.insert_one(doc)
        message.id = str(result.inserted_id)
        return message
    
    async def get_by_room(self, room_id: str, limit: int = 50, before: datetime = None) -> list[Message]:
        query = {"room_id": room_id}

        if before:
            query["created_at"] = {"$lt": before}   # before 시각 이전 메시지만

        cursor = self.collection.find(query) \
            .sort("created_at", -1) \
            .limit(limit)

        docs = await cursor.to_list(length=limit)

        return [
            Message(**{**doc, "_id": str(doc["_id"])})
            for doc in docs
        ]
        
    async def get_recent(self, room_id: str, limit: int = 30) -> list[Message]:
        cursor = self.collection.find({"room_id": room_id}) \
            .sort("created_at", -1) \
            .limit(limit)

        docs = await cursor.to_list(length=limit)

        return [
            Message(**{**doc, "_id": str(doc["_id"])})
            for doc in reversed(docs)   # 시간순으로 다시 뒤집기
        ]