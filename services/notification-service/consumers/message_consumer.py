from aiokafka import AIOKafkaConsumer
from core.config import settings
from core.redis_client import redis_client
from services.notify_service import NotifyService
import json
import asyncio

# ── 유저 온라인 상태 확인 ──────────────────────────────
# chat-service에서 연결 시 Redis에 저장한 상태값을 여기서 읽어옴
# "online" 이면 이미 메시지 받았으므로 알림 불필요
async def is_user_online(user_id: int) -> bool:
    status = await redis_client.get(f"user:{user_id}:status")
    return status == "online"

# ── 채팅방 멤버 목록 조회 ──────────────────────────────
# 누구에게 알림을 보낼지 결정하기 위해 방 멤버 전체를 가져옴
# Redis set 자료구조 사용 → 중복 없이 멤버 관리
async def get_room_members(room_id: str) -> list[int]:
    # Redis에서 채팅방 멤버 목록 조회
    members = await redis_client.smembers(f"room:{room_id}:members")
    return [int(uid) for uid in members]

# ── Kafka Consumer 메인 루프 ───────────────────────────
# main.py의 lifespan에서 asyncio.create_task()로 백그라운드 실행됨
# 앱이 살아있는 동안 계속 메시지 대기
async def handle_message(event: dict, notify_service: NotifyService):
    try:
        room_id      = event["room_id"]
        sender_id    = event["sender_id"]
        sender_name  = event["sender_username"]
        content      = event["content"]
        created_at   = event["created_at"]

        # 채팅방 멤버 중 오프라인 유저에게만 알림
        members = await get_room_members(room_id)

        for user_id in members:
            if user_id == sender_id:
                continue                              # 본인 제외

            if await is_user_online(user_id):
                continue                              # 온라인 유저 제외 (이미 받음)

            # 오프라인 유저에게 알림 저장
            await notify_service.save_notification(
                user_id=user_id,
                room_id=room_id,
                sender_username=sender_name,
                content=content,
                created_at=created_at,
            )

        print(f"[Kafka] processed message from room:{room_id}")

    except Exception as e:
        print(f"[Kafka] handle_message error: {e}")
        # 에러 발생해도 consumer는 계속 실행

async def consume():
    notify_service = NotifyService(redis_client)

    # Kafka 뜰 때까지 무한 재시도
    while True:
        try:
            consumer = AIOKafkaConsumer(
                "chat-messages",
                bootstrap_servers=settings.KAFKA_URL,
                group_id=settings.KAFKA_GROUP_ID,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="latest",
                retry_backoff_ms=1000,        # 재시도 간격
            )
            await consumer.start()
            print("Kafka Consumer started")
            break

        except Exception as e:
            print(f"Kafka 연결 재시도 중: {e}")
            await asyncio.sleep(5)

    try:
        async for msg in consumer:
            await handle_message(msg.value, notify_service)

    except asyncio.CancelledError:
        print("Consumer cancelled")
    finally:
        await consumer.stop()
        print("Kafka Consumer stopped")