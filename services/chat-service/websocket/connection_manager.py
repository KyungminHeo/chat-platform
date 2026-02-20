from fastapi import WebSocket
from redis.asyncio import Redis
import json

class ConnectionManager():
    def __init__(self):
        # 현재 서버 인스턴스에 연결된 WebSocket만 관리
        # { room_id: { user_id: WebSocket } }
        self.active_connections: dict[str, dict[int, WebSocket]] = {}
        
    # ── 연결 ───────────────────────────────────────────
    async def connect(self, websocket: WebSocket, room_id: str, user_id: int, redis: Redis):
        await websocket.accept()
        
        # 메모리에 연결 등록
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        self.active_connections[room_id][user_id] = websocket
        
        # Redis에 온라인 상태 저장 (다른 서버 인스턴스도 알 수 있게)
        await redis.sadd(f"room:{room_id}:online", user_id)
        await redis.setex(f"user:{user_id}:status", 300, "online")
        
        print(f"[WS] user:{user_id} connected to room:{room_id}")
    
    # ── 연결 해제 ──────────────────────────────────────
    async def disconnect(self, room_id: str, user_id: int, redis: Redis):
        
        # 메모리에서 제거
        if room_id not in self.active_connections:
            self.active_connections[room_id].pop(user_id, None)
            # 빈 방이면 방도 제거
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
                
        # Redis 온라인 상태 제거
        await redis.srem(f"room:{room_id}:online", user_id)
        await redis.delete(f"user:{user_id}:status")
        
        print(f"[WS] user:{user_id} disconnected from room:{room_id}")
        
    # ── 방 전체에 메시지 브로드캐스트 ─────────────────
    async def broadcast(self, room_id: str, message: dict):
        connections = self.active_connections.get(room_id, {})

        disconnected = []
        for user_id, websocket in connections.items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(user_id)  # 끊긴 연결 수집
        
        # 끊긴 연결 정리
        for user_id in disconnected:
            connections.pop(user_id, None)
        
    # ── 특정 유저에게만 전송 ───────────────────────────
    async def send_to_user(self, room_id: str, user_id: int, message: dict):
        connections = self.active_connections.get(room_id, {})
        websocket = connections.get(user_id)
        if websocket:
            await websocket.send_json(message)

    # ── 온라인 유저 목록 조회 (Redis 기반) ────────────
    async def get_online_users(self, room_id: str, redis: Redis) -> list[int]:
        members = await redis.smembers(f"room:{room_id}:online")
        return [int(uid) for uid in members]
    
    
# 서비스 전체에서 단일 인스턴스 사용
manager = ConnectionManager()