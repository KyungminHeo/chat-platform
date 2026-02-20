from aiokafka import AIOKafkaProducer
import json
import asyncio
from core.config import settings

producer: AIOKafkaProducer = None

async def get_kafka_producer() -> AIOKafkaProducer:
    return producer

async def start_producer():
    global producer

    # Kafka 뜰 때까지 무한 재시도
    while True:
        try:
            producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_URL,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await producer.start()
            print("Kafka Producer started")
            break

        except Exception as e:
            print(f"Kafka 연결 재시도 중: {e}")
            try:
                await producer.stop()
            except Exception:
                pass
            producer = None
            await asyncio.sleep(5)

async def stop_producer():
    global producer
    if producer:
        await producer.stop()
        producer = None
        print("Kafka Producer stopped")

async def publish(topic: str, message: dict):
    await producer.send_and_wait(topic, message)