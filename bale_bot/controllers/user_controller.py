from sqlalchemy.future import select
from sqlalchemy.sql import func

from bale_bot.database import bale_async_session_maker
from bale_bot.database.models import BaleUser, BaleUserSettings
from logger import get_logger

logger = get_logger(__name__)


class BaleUserController:
    """User controller for Bale bot - uses separate Bale database"""

    @staticmethod
    async def register_user(user_data: dict):
        """Register a new Bale user or update existing one."""
        async with bale_async_session_maker() as session:
            try:
                # Check if user exists
                result = await session.execute(
                    select(BaleUser).where(BaleUser.user_id == user_data['id'])
                )
                user = result.scalars().first()

                if user:
                    # Update existing user
                    user.username = user_data.get('username')
                    user.first_name = user_data.get('first_name')
                    user.last_name = user_data.get('last_name')
                    user.last_activity = func.now()
                    logger.info(f"Updated existing Bale user: {user_data['id']}")
                else:
                    # Create new user
                    user = BaleUser(
                        user_id=user_data['id'],
                        username=user_data.get('username'),
                        first_name=user_data.get('first_name'),
                        last_name=user_data.get('last_name'),
                        is_bot=user_data.get('is_bot', False),
                        language_code=user_data.get('language_code'),
                    )
                    session.add(user)
                    logger.info(f"Created new Bale user: {user_data['id']}")

                    # Create default settings
                    settings = BaleUserSettings(
                        user_id=user_data['id'],
                        download_quality='MP3_320',
                        make_zip=True,
                        language='en'
                    )
                    session.add(settings)

                await session.commit()
                return True, user

            except Exception as e:
                await session.rollback()
                logger.error(f"Error registering Bale user: {str(e)}", exc_info=True)
                return False, str(e)

    @staticmethod
    async def get_user_settings(user_id: int):
        """Get user settings."""
        async with bale_async_session_maker() as session:
            try:
                result = await session.execute(
                    select(BaleUserSettings).where(BaleUserSettings.user_id == user_id)
                )
                settings = result.scalars().first()

                if settings:
                    return True, {
                        'download_quality': settings.download_quality,
                        'make_zip': settings.make_zip,
                        'language': settings.language
                    }
                else:
                    # Create default settings if not found
                    settings = BaleUserSettings(
                        user_id=user_id,
                        download_quality='MP3_320',
                        make_zip=True,
                        language='en'
                    )
                    session.add(settings)
                    await session.commit()
                    return True, {
                        'download_quality': 'MP3_320',
                        'make_zip': True,
                        'language': 'en'
                    }

            except Exception as e:
                logger.error(f"Error getting Bale user settings: {str(e)}", exc_info=True)
                return False, str(e)

    @staticmethod
    async def update_user_settings(user_id: int, settings_update: dict):
        """Update user settings."""
        async with bale_async_session_maker() as session:
            try:
                result = await session.execute(
                    select(BaleUserSettings).where(BaleUserSettings.user_id == user_id)
                )
                settings = result.scalars().first()

                if settings:
                    for key, value in settings_update.items():
                        if hasattr(settings, key):
                            setattr(settings, key, value)
                    await session.commit()
                    return True, "Settings updated"
                else:
                    return False, "Settings not found"

            except Exception as e:
                await session.rollback()
                logger.error(f"Error updating Bale user settings: {str(e)}", exc_info=True)
                return False, str(e)

    @staticmethod
    async def get_user_downloads(user_id: int, limit: int = 5, offset: int = 0):
        """Get user's download history."""
        from bale_bot.database.models import BaleUserDownload
        async with bale_async_session_maker() as session:
            result = await session.execute(
                select(BaleUserDownload)
                .where(BaleUserDownload.user_id == user_id)
                .order_by(BaleUserDownload.downloaded_at.desc())
                .offset(offset)
                .limit(limit)
            )
            downloads = result.scalars().all()
            return True, downloads
