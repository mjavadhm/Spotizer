from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    # Note: Email/password auth disabled - Telegram-only auth
    user_id: Optional[int] = None


class UserUpdate(UserBase):
    password: Optional[str] = Field(None, min_length=6)


class UserSettingsBase(BaseModel):
    download_quality: Optional[str] = "MP3_320"
    make_zip: Optional[bool] = True
    language: Optional[str] = "en"


class UserSettingsUpdate(UserSettingsBase):
    pass


class UserSettingsResponse(UserSettingsBase):
    user_id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserResponse(UserBase):
    user_id: int
    is_premium: bool = False
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    settings: Optional[UserSettingsResponse] = None

    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    pass  # No password for Telegram-only auth


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


class TelegramLoginData(BaseModel):
    """Data received from Telegram Login Widget"""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class TelegramBotAuth(BaseModel):
    """Data for authentication from Telegram bot"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = False
    auth_token: str  # Bot-generated token for verification


class TelegramAuthResponse(BaseModel):
    """Response for Telegram authentication"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    is_new_user: bool = False
