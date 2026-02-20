from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from bson import ObjectId

class Message(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    room_id: str
    sender_id: int
    sender_username: str
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }