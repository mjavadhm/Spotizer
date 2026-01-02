from datetime import timedelta
from typing import Annotated
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_db
from ..schemas.user import (
    UserCreate, UserResponse, Token,
    TelegramLoginData, TelegramBotAuth, TelegramAuthResponse
)
from ..dependencies import (
    authenticate_user, create_user, get_user_by_email,
    create_access_token, get_current_user,
    verify_telegram_login, verify_telegram_bot_auth_token,
    get_or_create_telegram_user, generate_telegram_bot_auth_token,
    get_user_by_id
)
from ..config import settings
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """Register a new user"""
    # Check if user already exists
    existing_user = await get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    user = await create_user(
        db,
        email=user_data.email,
        password=user_data.password,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        user_id=user_data.user_id
    )

    logger.info(f"New user registered: {user.email}")
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_async_db)
):
    """Login and get access token"""
    user = await authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.user_id, "email": user.email},
        expires_delta=access_token_expires
    )

    logger.info(f"User logged in: {user.email}")
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_user)
):
    """Refresh access token"""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.user_id, "email": current_user.email},
        expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer")


# ==================== Telegram Authentication ====================

@router.post("/telegram", response_model=TelegramAuthResponse)
async def login_with_telegram(
    telegram_data: TelegramLoginData,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Authenticate using Telegram Login Widget.

    This endpoint verifies the data sent from Telegram's Login Widget
    and returns a JWT token for API access.

    The hash is verified using the bot token to ensure the data
    came from Telegram.
    """
    # Verify the Telegram login data
    if not verify_telegram_login(telegram_data):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram authentication data"
        )

    # Get or create user
    user, is_new = await get_or_create_telegram_user(
        db,
        user_id=telegram_data.id,
        username=telegram_data.username,
        first_name=telegram_data.first_name,
        last_name=telegram_data.last_name,
        photo_url=telegram_data.photo_url
    )

    # Generate access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.user_id, "email": user.email},
        expires_delta=access_token_expires
    )

    logger.info(f"Telegram login successful for user {user.user_id} (new: {is_new})")

    return TelegramAuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        is_new_user=is_new
    )


@router.post("/telegram/bot", response_model=TelegramAuthResponse)
async def login_from_bot(
    auth_data: TelegramBotAuth,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Authenticate using a token generated by the Telegram bot.

    The bot generates a one-time token for the user, which can be
    used to authenticate on the web interface.

    Flow:
    1. User requests login link from bot (/login command)
    2. Bot generates auth_token and sends login URL to user
    3. User clicks link and this endpoint is called
    4. Backend verifies token and returns JWT
    """
    # Verify the bot-generated token
    verified_user_id = verify_telegram_bot_auth_token(auth_data.auth_token)

    if verified_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token"
        )

    # Verify user_id matches
    if verified_user_id != auth_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID mismatch"
        )

    # Get or create user
    user, is_new = await get_or_create_telegram_user(
        db,
        user_id=auth_data.user_id,
        username=auth_data.username,
        first_name=auth_data.first_name,
        last_name=auth_data.last_name,
        language_code=auth_data.language_code,
        is_premium=auth_data.is_premium or False
    )

    # Generate access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.user_id, "email": user.email},
        expires_delta=access_token_expires
    )

    logger.info(f"Bot login successful for user {user.user_id}")

    return TelegramAuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
        is_new_user=is_new
    )


@router.post("/telegram/generate-token")
async def generate_bot_auth_token(
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Generate an authentication token for a Telegram user.

    This endpoint is meant to be called by the bot (with proper authentication)
    to generate a login token for a user.

    Note: In production, this should be protected and only accessible by the bot.
    """
    # Check if user exists
    user = await get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. User must start the bot first."
        )

    # Generate token
    token = generate_telegram_bot_auth_token(user_id)

    return {
        "auth_token": token,
        "expires_in": settings.TELEGRAM_AUTH_EXPIRY_SECONDS,
        "user_id": user_id
    }


@router.get("/telegram/verify")
async def verify_telegram_session(
    current_user: User = Depends(get_current_user)
):
    """
    Verify current Telegram session is valid.

    Returns user info if the session is valid.
    """
    return {
        "valid": True,
        "user": UserResponse.model_validate(current_user)
    }
