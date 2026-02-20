from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User

class UserRepository:
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def create(self, email: str, username: str, hashed_password: str) -> User:
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
        )
        self.db.add(user)
        await self.db.flush()   # DB에 반영하되 트랜잭션은 아직 유지
        await self.db.refresh(user)  # DB가 생성한 id, created_at 등 다시 로딩
        return user
    
    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def update_active(self, user_id: int, is_active: bool) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.is_active = is_active
        await self.db.flush()
        await self.db.refresh(user)
        return user