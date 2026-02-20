from pydantic import BaseModel
from datetime import datetime

# 채팅방 생성
class RoomCreate(BaseModel):
    name: str
    member_ids: list[int]

# 채팅방 응답
class RoomResponse(BaseModel):
    room_id: str
    name: str
    member_ids: list[int]

# WebSocket 수신 메시지 형식
class WSMessageReceive(BaseModel):
    content: str
    room_id: str
    
# WebSocket 송신 메시지 형식
class WSMessageSend(BaseModel):
    type: str                  # "message" | "join" | "leave"
    room_id: str
    sender_id: int
    sender_username: str
    content: str
    created_at: str