from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis

from core.redis_client import get_redis
from services.notify_service import NotifyService

router = APIRouter(prefix="/api/notify", tags=["notifications"])

def get_notify_service(redis: Redis = Depends(get_redis)) -> NotifyService:
    return NotifyService(redis)

@router.get("/{user_id}")
async def get_notifications(user_id: int, service: NotifyService = Depends(get_notify_service)):
    notifications = await service.get_notifications(user_id)
    unread = await service.get_unread_count(user_id)
    return {
        "user_id": user_id,
        "unread_count": unread,
        "notifications": notifications,
    }
    
@router.post("/{user_id}/read")
async def mark_all_read(user_id: int, service: NotifyService = Depends(get_notify_service)):
    await service.mark_all_read(user_id)
    return {"message": "모든 알림을 읽음 처리했습니다."}

@router.get("/health")
async def health():
    return {"status": "ok"}