from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ── Redis ──────────────────────────────────────────
    REDIS_URL: str

    # ── Kafka ──────────────────────────────────────────
    KAFKA_URL: str
    KAFKA_GROUP_ID: str

settings = Settings()