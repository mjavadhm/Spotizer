import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..database import get_async_db
from ..models.user import User, UserSettings
from ..schemas.user import (
    UserResponse, UserUpdate, UserSettingsResponse, UserSettingsUpdate
)
from ..dependencies import get_current_user, get_password_hash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user's profile"""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update current user's profile"""
    update_data = user_update.model_dump(exclude_unset=True)

    if 'password' in update_data:
        update_data['hashed_password'] = get_password_hash(update_data.pop('password'))

    if update_data:
        stmt = (
            update(User)
            .where(User.user_id == current_user.user_id)
            .values(**update_data)
        )
        await db.execute(stmt)
        await db.commit()
        await db.refresh(current_user)

    logger.info(f"User profile updated: {current_user.user_id}")
    return current_user


@router.get("/me/settings", response_model=UserSettingsResponse)
async def get_my_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get current user's settings"""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.user_id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        # Create default settings
        settings = UserSettings(
            user_id=current_user.user_id,
            download_quality="MP3_320",
            make_zip=True,
            language="en"
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return settings


@router.patch("/me/settings", response_model=UserSettingsResponse)
async def update_my_settings(
    settings_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update current user's settings"""
    update_data = settings_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No settings to update"
        )

    # Check if settings exist
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.user_id)
    )
    settings = result.scalar_one_or_none()

    if settings:
        # Update existing settings
        stmt = (
            update(UserSettings)
            .where(UserSettings.user_id == current_user.user_id)
            .values(**update_data)
        )
        await db.execute(stmt)
    else:
        # Create new settings
        settings = UserSettings(
            user_id=current_user.user_id,
            **update_data
        )
        db.add(settings)

    await db.commit()

    # Fetch updated settings
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.user_id)
    )
    settings = result.scalar_one()

    logger.info(f"User settings updated: {current_user.user_id}")
    return settings


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get a user's public profile"""
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user
