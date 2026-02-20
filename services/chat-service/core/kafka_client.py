from aiokafka import AIOKafkaProducer
import json
from core.config import settings

producer: AIOKafkaProducer = None

async def get_kafka_producer() -> AIOKafkaProducer:
    return producer

async def start_producer():
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_URL,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    print("Kafka Producer started")
    
async def stop_producer():
    global producer
    if producer:
        await producer.stop()
        print("Kafka Producer stopped")
        
async def publish(topic: str, message: dict):
    await producer.send_and_wait(topic, message) # Kafka가 메시지 받았다고 확인할 때까지 대기 데이터 유실 방지
                  