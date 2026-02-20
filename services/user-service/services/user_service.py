from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import json

from repositories.user_repo import UserRepository
from schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    
    def __init__(self, db: AsyncSession, redis: Redis):
        self.repo = UserRepository(db)
        self.redis = redis
        
    # ── 비밀번호 ───────────────────────────────────────
    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)
    
    def verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)
    
    # ── JWT ────────────────────────────────────────────
    def create_access_token(self, user_id: int) -> str:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        return jwt.encode(
            {"sub": str(user_id), "exp": expire},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
    
    # ── 회원가입 ───────────────────────────────────────
    async def register(self, data: UserCreate) -> UserResponse:
        # 중복 체크
        if await self.repo.get_by_email(data.email):
            raise ValueError("이미 사용 중인 이메일입니다.")
        if await self.repo.get_by_username(data.username):
            raise ValueError("이미 사용 중인 유저명입니다.")

        user = await self.repo.create(
            email=data.email,
            username=data.username,
            hashed_password=self.hash_password(data.password),
        )
        return UserResponse.model_validate(user)
    
    # ── 로그인 ───────────────────────────────────────
    async def login(self, data: UserLogin) -> TokenResponse:
        user = await self.repo.get_by_email(data.email)

        if not user or not self.verify_password(data.password, user.hashed_password):
            raise ValueError("이메일 또는 비밀번호가 올바르지 않습니다.")
        if not user.is_active:
            raise ValueError("비활성화된 계정입니다.")
        
        #chat-service 에서 user_id > username 조회할 수 있도록 캐시
        await self.redis.setex(f"user:{user.id}:username", 3600 ,user.username)

        return TokenResponse(access_token=self.create_access_token(user.id))
    
    # ── 유저 조회 + 캐싱 ───────────────────────────────
    async def get_user(self, user_id: int) -> UserResponse:
        cache_key = f"user:{user_id}"

        # 1. 캐시 확인
        cached = await self.redis.get(cache_key)
        if cached:
            return UserResponse(**json.loads(cached))   # 캐시 히트 → DB 안 감

        # 2. 캐시 없으면 DB 조회
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise ValueError("유저를 찾을 수 없습니다.")

        response = UserResponse.model_validate(user)

        # 3. 캐시 저장 (5분 TTL)
        await self.redis.setex(
            cache_key,
            300,
            response.model_dump_json()
        )

        return response