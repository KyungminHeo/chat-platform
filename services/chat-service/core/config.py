from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ── MongoDB ────────────────────────────────────────
    MONGO_URL: str
    MONGO_DB: str

    # ── Redis ──────────────────────────────────────────
    REDIS_URL: str

    # ── Kafka ──────────────────────────────────────────
    KAFKA_URL: str

    # ── JWT (토큰 검증용) ───────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str

settings = Settings()