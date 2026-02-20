from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from core.config import settings

# 엔진 생성 - 커넥션 풀 설정이 대용량 트래픽 핵심
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,          # 기본 커넥션 수
    max_overflow=40,       # 풀 초과 시 추가 허용 커넥션
    pool_timeout=30,       # 커넥션 못 얻으면 30초 후 에러
    pool_recycle=1800,     # 30분마다 커넥션 재생성 (끊김 방지)
    echo=False
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

# 의존성 주입용 - 요청마다 세션 열고 닫음
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise