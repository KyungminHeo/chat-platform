from motor.motor_asyncio import AsyncIOMotorCollection
from redis.asyncio import Redis
from aiokafka import AIOKafkaProducer
from datetime import datetime
import json

from repositories.message_repo import MessageRepository
from models.message import Message
from schemas.chat import WSMessageSend
from websocket.connection_manager import manager
from core.kafka_client import publish

class ChatService:
    
    def __init__(self, collection: AsyncIOMotorCollection, redis: Redis):
        self.repo = MessageRepository(collection)
        self.redis = redis
        
    # ── 메시지 전송 핵심 로직 ──────────────────────────
    async def send_message(self, room_id: str, sender_id: int, sender_username: str, content: str) -> WSMessageSend:
        
        # 1. MongoDB에 저장
        message = Message(
            room_id=room_id,
            sender_id=sender_id,
            sender_username=sender_username,
            content=content,
            created_at=datetime.utcnow()
        )
        saved = await self.repo.save(message)
        
        # 2. 브로드캐스트용 응답 객체 생성
        response = WSMessageSend(
            type="message",
            room_id=room_id,
            sender_id=sender_id,
            sender_username=sender_username,
            content=content,
            created_at=saved.created_at.isoformat()
        )
        
        # 3. 같은 방 연결된 유저들에게 즉시 전송
        await manager.broadcast(room_id, response.model_dump())
        
        # 4. kafka에 이벤트 발행 -> notification-service가 구독
        await publish("chat-messages", {
            "room_id": room_id,
            "sender_id": sender_id,
            "sender_username": sender_username,
            "content": content,
            "created_at": saved.created_at.isoformat(),
        })
        
        # 5. Redis에 최근 메시지 캐시 (채팅방 입장 시 빠르게 로딩)
        cache_key = f"room:{room_id}:recent"
        await self.redis.lpush(cache_key, response.model_dump_json())
        await self.redis.ltrim(cache_key, 0, 29)   # 최근 30개만 유지
        await self.redis.expire(cache_key, 3600)   # 1시간 TTL
        
        return response
    
    # ── 채팅방 입장 시 최근 메시지 로딩 ──────────────
    async def get_recent_messages(self, room_id: str) -> list[dict]:
        cache_key = f"room:{room_id}:recent"
        
        # 1. Redis 캐시 확인
        cached = await self.redis.lrange(cache_key, 0, -1)
        if cached:
            messages = [json.loads(m) for m in cached]
            return list(reversed(messages))   # 시간순 정렬
        
        # 2. 캐시 없으면 MongoDB 조회
        messages = await self.repo.get_recent(room_id, limit=30)
        return [m.model_dump(mode="json") for m in messages]
    
    # ── 이전 메시지 페이지네이션 ──────────────────────
    async def get_messages_before(self, room_id: str, before: datetime, limit: int = 50) -> list[dict]:
        messages = await self.repo.get_by_room(room_id, limit, before)
        return [m.model_dump(mode="json") for m in messages]
        
    # ── 채팅방 입장 이벤트 ────────────────────────────
    async def user_joined(self, room_id: str, user_id: int, username: str):
        event = {
            "type": "join",
            "room_id": room_id,
            "sender_id": user_id,
            "sender_username": username,
            "content": f"{username}님이 입장했습니다.",
            "created_at": datetime.utcnow().isoformat(),
        }
        await manager.broadcast(room_id, event)
    
    # ── 채팅방 퇴장 이벤트 ────────────────────────────
    async def user_left(self, room_id: str, user_id: int, username: str):
        event = {
            "type": "leave",
            "room_id": room_id,
            "sender_id": user_id,
            "sender_username": username,
            "content": f"{username}님이 퇴장했습니다.",
            "created_at": datetime.utcnow().isoformat(),
        }
        await manager.broadcast(room_id, event)