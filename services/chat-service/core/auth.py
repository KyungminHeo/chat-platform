from jose import jwt, JWTError
from fastapi import WebSocket
from core.config import settings

async def verify_token_ws(websocket: WebSocket, token: str) -> int:
    """
    WebSocket 연결 시 JWT 토큰 검증
    성공 시 user_id 반환
    실패 시 연결 종료
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        user_id = payload.get("sub")
        
        if not user_id:
            await websocket.close(code=1008)
            raise ValueError("토큰에 user_id 없음")
        
        return int(user_id)
    
    except JWTError:
        await websocket.close(1008)
        raise ValueError("유효하지 않은 토큰")