from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging
import hashlib
import hmac
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .config import settings
from .database import get_db, get_async_db
from .models.user import User, UserSettings
from .schemas.user import TokenData, TelegramLoginData

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None:
            return None
        return TokenData(user_id=user_id, email=email)
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """Get the current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = decode_token(token)
    if token_data is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.user_id == token_data.user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_async_db)
) -> Optional[User]:
    """Get the current user if authenticated, otherwise return None"""
    if token is None:
        return None

    token_data = decode_token(token)
    if token_data is None:
        return None

    result = await db.execute(select(User).where(User.user_id == token_data.user_id))
    user = result.scalar_one_or_none()

    return user


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get a user by email"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """Get a user by ID"""
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password"""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_user(db: AsyncSession, email: str, password: str, **kwargs) -> User:
    """Create a new user"""
    import random

    # Generate a unique user_id
    user_id = kwargs.get('user_id') or random.randint(1000000000, 9999999999)

    user = User(
        user_id=user_id,
        email=email,
        hashed_password=get_password_hash(password),
        username=kwargs.get('username'),
        first_name=kwargs.get('first_name'),
        last_name=kwargs.get('last_name')
    )
    db.add(user)
    await db.flush()

    # Create default settings
    user_settings = UserSettings(
        user_id=user.user_id,
        download_quality="MP3_320",
        make_zip=True,
        language="en"
    )
    db.add(user_settings)

    await db.commit()
    await db.refresh(user)

    return user


# ==================== Telegram Authentication ====================

def verify_telegram_login(data: TelegramLoginData) -> bool:
    """
    Verify Telegram Login Widget data.

    Telegram sends data with a hash that we need to verify using the bot token.
    See: https://core.telegram.org/widgets/login#checking-authorization
    """
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN not configured")
        return False

    # Check if auth_date is not too old
    current_time = int(time.time())
    if current_time - data.auth_date > settings.TELEGRAM_AUTH_EXPIRY_SECONDS:
        logger.warning(f"Telegram auth expired: {current_time - data.auth_date}s old")
        return False

    # Build the data-check-string
    data_dict = {
        "id": data.id,
        "first_name": data.first_name,
        "auth_date": data.auth_date,
    }
    if data.last_name:
        data_dict["last_name"] = data.last_name
    if data.username:
        data_dict["username"] = data.username
    if data.photo_url:
        data_dict["photo_url"] = data.photo_url

    # Sort by key and create check string
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(data_dict.items())
    )

    # Create secret key from bot token
    secret_key = hashlib.sha256(settings.BOT_TOKEN.encode()).digest()

    # Calculate hash
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    # Compare hashes
    is_valid = hmac.compare_digest(calculated_hash, data.hash)

    if not is_valid:
        logger.warning(f"Telegram auth hash mismatch for user {data.id}")

    return is_valid


def generate_telegram_bot_auth_token(user_id: int) -> str:
    """
    Generate a token for bot-initiated authentication.

    This token can be generated by the bot and sent to the user,
    who can then use it to authenticate on the web.
    """
    # Create a token with user_id and timestamp
    payload = {
        "user_id": user_id,
        "type": "telegram_bot_auth",
        "iat": int(time.time())
    }

    # Sign with secret key
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token


def verify_telegram_bot_auth_token(token: str) -> Optional[int]:
    """
    Verify a bot-generated authentication token.

    Returns the user_id if valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        if payload.get("type") != "telegram_bot_auth":
            return None

        # Check if token is not too old
        iat = payload.get("iat", 0)
        if int(time.time()) - iat > settings.TELEGRAM_AUTH_EXPIRY_SECONDS:
            return None

        return payload.get("user_id")
    except JWTError:
        return None


async def get_or_create_telegram_user(
    db: AsyncSession,
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    language_code: Optional[str] = None,
    is_premium: bool = False,
    photo_url: Optional[str] = None
) -> Tuple[User, bool]:
    """
    Get an existing user or create a new one from Telegram data.

    Returns a tuple of (user, is_new_user).
    """
    # Try to find existing user
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    is_new = False

    if user:
        # Update user information
        user.username = username or user.username
        user.first_name = first_name or user.first_name
        user.last_name = last_name or user.last_name
        user.language_code = language_code or user.language_code
        user.is_premium = is_premium
        user.last_activity = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
        logger.info(f"Updated Telegram user: {user_id}")
    else:
        # Create new user
        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            is_premium=is_premium,
            is_active=True
        )
        db.add(user)
        await db.flush()

        # Create default settings
        user_settings = UserSettings(
            user_id=user.user_id,
            download_quality="MP3_320",
            make_zip=True,
            language=language_code or "en"
        )
        db.add(user_settings)

        await db.commit()
        await db.refresh(user)
        is_new = True
        logger.info(f"Created new Telegram user: {user_id}")

    return user, is_new
