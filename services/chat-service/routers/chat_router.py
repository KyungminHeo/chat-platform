from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from redis.asyncio import Redis
from datetime import datetime

from core.mongo_client import message_collection
from core.redis_client import get_redis
from websocket.connection_manager import manager
from services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])

# ── 의존성 주입 헬퍼 ───────────────────────────────────
def get_chat_service(redis: Redis = Depends(get_redis)) -> ChatService:
    return ChatService(message_collection, redis)

# ── WebSocket 엔드포인트 ────────────────────────
@router.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    user_id: int = Query(...),           # ws://host/api/chat/ws/room1?user_id=1
    username: str = Query(...),          # ws://host/api/chat/ws/room1?username=홍길동
    redis: Redis = Depends(get_redis),
    service: ChatService = Depends(get_chat_service),
):
    # 1. 연결
    await manager.connect(websocket, room_id, user_id, redis)

    # 2. 입장 이벤트 브로드캐스트
    await service.user_joined(room_id, user_id, username)

    # 3. 최근 메시지 전송 (입장 시 이전 대화 로딩)
    recent = await service.get_recent_messages(room_id)
    await websocket.send_json({
        "type": "history",
        "messages": recent,
    })

    try:
        # 4. 메시지 수신 루프
        while True:
            data = await websocket.receive_json()

            # 클라이언트에서 오는 형식: {"content": "안녕하세요"}
            content = data.get("content", "").strip()
            if not content:
                continue

            await service.send_message(
                room_id=room_id,
                sender_id=user_id,
                sender_username=username,
                content=content,
            )

    except WebSocketDisconnect:
        # 5. 연결 해제
        await manager.disconnect(room_id, user_id, redis)
        await service.user_left(room_id, user_id, username)
        
# ── HTTP 엔드포인트 ────────────────────────────────────
@router.get("/rooms/{room_id}/messages")
async def get_messages(
    room_id: str,
    before: datetime = Query(default=None),   # 커서 페이지네이션
    limit: int = Query(default=50, le=100),   # 최대 100개
    service: ChatService = Depends(get_chat_service),
):
    if before:
        messages = await service.get_messages_before(room_id, before, limit)
    else:
        messages = await service.get_recent_messages(room_id)
        
    return {"messages": messages}

@router.get("/rooms/{room_id}/online")
async def get_online_users(room_id: str, redis: Redis = Depends(get_redis)):
    users = await manager.get_online_users(room_id, redis)
    return {"room_id": room_id, "online_users": users}

@router.get("/health")
async def health():
    return {"status": "ok"}