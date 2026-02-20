from pydantic import BaseModel, EmailStr
from datetime import datetime

# 회원가입 요청
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    
# 로그인 요청
class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
# 응답 (password 절대 포함 안함)
class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}  # SQLAlchemy 모델 → Pydantic 자동 변환

# JWT 토큰 응답
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
