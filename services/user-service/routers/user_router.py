from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from core.database import get_db
from core.redis_client import get_redis
from services.user_service import UserService
from schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse

router = APIRouter(prefix="/api/users", tags=["users"])


# ── 의존성 주입 헬퍼 ───────────────────────────────────
def get_user_service(db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)) -> UserService:
    return UserService(db, redis)


# ── 엔드포인트 ─────────────────────────────────────────
@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserCreate, service: UserService = Depends(get_user_service)):
    try:
        return await service.register(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, service: UserService = Depends(get_user_service)):
    try:
        return await service.login(data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, service: UserService = Depends(get_user_service)):
    try:
        return await service.get_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}
