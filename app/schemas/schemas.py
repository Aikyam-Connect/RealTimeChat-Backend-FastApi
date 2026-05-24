from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None

class User(UserBase):
    id: int
    google_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Auth Schemas
class GoogleLogin(BaseModel):
    credential: str  # The JWT token from Google

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Message Schemas
class MessageBase(BaseModel):
    content: str

class MessageCreate(MessageBase):
    room_id: int

class MessageResponse(MessageBase):
    id: int
    sender_id: int
    room_id: int
    message_type: Optional[str] = "text"
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    created_at: datetime
    sender_name: Optional[str] = None

    class Config:
        from_attributes = True

# Room Schemas
class RoomBase(BaseModel):
    name: str
    is_group: bool = False

class RoomCreate(RoomBase):
    pass

class RoomResponse(RoomBase):
    id: int
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True
