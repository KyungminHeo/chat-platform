from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ── PostgreSQL ─────────────────────────────────────
    DATABASE_URL: str

    # ── Redis ──────────────────────────────────────────
    REDIS_URL: str

    # ── JWT ────────────────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

settings = Settings()