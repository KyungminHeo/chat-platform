from redis.asyncio import Redis
import json
from datetime import datetime

class NotifyService:
    def __init__(self, redis: Redis):
        self.redis = redis
    
    # ── 알림 저장 ──────────────────────────────────────
    async def save_notification(self, user_id: int, room_id: str, sender_username: str, content: str, created_at: str):
        notification = {
            "room_id": room_id,
            "sender_username": sender_username,
            "content": content[:50],          # 미리보기 50자
            "created_at": created_at,
            "is_read": False,
        }
        
        key = f"notifications:{user_id}"
        
        # Redis List에 알림 추가 (최신순)
        await self.redis.lpush(key, json.dumps(notification))
        await self.redis.ltrim(key, 0, 99)        # 최대 100개 유지
        await self.redis.expire(key, 86400 * 7)   # 7일 TTL
        
        # 읽지 않은 알림 카운트 증가
        await self.redis.incr(f"unread:{user_id}")
        await self.redis.expire(f"unread:{user_id}", 86400 * 7)
        
    # ── 알림 목록 조회 ────────────────────────────────
    async def get_notifications(self, user_id: int) -> list[dict]:
        key = f"notifications:{user_id}"
        items = await self.redis.lrange(key, 0, 49)   # 최근 50개
        return [json.loads(item) for item in items]
    
    # ── 읽지 않은 알림 수 ──────────────────────────────
    async def get_unread_count(self, user_id: int) -> int:
        count = await self.redis.get(f"unread:{user_id}")
        return int(count) if count else 0
    
    # ── 알림 전체 읽음 처리 ────────────────────────────
    async def mark_all_read(self, user_id: int):
        await self.redis.delete(f"unread:{user_id}")
        
        # 알림 목록에서 is_read 전부 True로 업데이트
        key = f"notifications:{user_id}"
        items = await self.redis.lrange(key, 0, -1)
        
        pipeline = self.redis.pipeline()

        for idx, item in enumerate(items):
            notification = json.loads(item)
            notification["is_read"] = True
            pipeline.lset(key, idx, json.dumps(notification))

        await pipeline.execute()