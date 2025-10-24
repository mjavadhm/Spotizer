import logging
from sqlalchemy.future import select
from database.session import async_session_maker
from models.base import User, UserSettings, UserActivity, UserDownload
from utils.url_validator import validate_settings

logger = logging.getLogger(__name__)

class UserController:
    @staticmethod
    async def register_user(user_data):
        """Register or update user information."""
        async with async_session_maker() as session:
            async with session.begin():
                user_id = user_data.get('id')
                if not user_id:
                    return False, "Invalid user data: Missing user ID"

                user = await session.get(User, user_id)
                if user:
                    # Update existing user
                    user.username = user_data.get('username')
                    user.first_name = user_data.get('first_name')
                    user.last_name = user_data.get('last_name')
                    user.language_code = user_data.get('language_code')
                    user.is_premium = user_data.get('is_premium', False)
                    user.is_bot = user_data.get('is_bot', False)
                else:
                    # Create new user
                    user = User(
                        user_id=user_id,
                        username=user_data.get('username'),
                        first_name=user_data.get('first_name'),
                        last_name=user_data.get('last_name'),
                        language_code=user_data.get('language_code'),
                        is_premium=user_data.get('is_premium', False),
                        is_bot=user_data.get('is_bot', False)
                    )
                    session.add(user)
                    # Create default settings
                    user_settings = UserSettings(user_id=user_id)
                    session.add(user_settings)

            await session.commit()
            return True, "User registered successfully"

    @staticmethod
    async def update_user_settings(user_id, settings):
        """Update user settings."""
        async with async_session_maker() as session:
            async with session.begin():
                valid, message = validate_settings(settings)
                if not valid:
                    return False, message

                user_settings = await session.get(UserSettings, user_id)
                if not user_settings:
                    user_settings = UserSettings(user_id=user_id)
                    session.add(user_settings)

                for key, value in settings.items():
                    setattr(user_settings, key, value)

                await session.commit()
                return True, "Settings updated successfully"

    @staticmethod
    async def get_user_settings(user_id):
        """Get user settings."""
        async with async_session_maker() as session:
            user_settings = await session.get(UserSettings, user_id)
            if user_settings:
                return True, {
                    "download_quality": user_settings.download_quality,
                    "make_zip": user_settings.make_zip,
                    "language": user_settings.language
                }
            return False, "Settings not found"

    @staticmethod
    async def get_user_info(user_id):
        """Get user information."""
        async with async_session_maker() as session:
            user = await session.get(User, user_id)
            if user:
                return True, {
                    "user_id": user.user_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_bot": user.is_bot,
                    "language_code": user.language_code,
                    "is_premium": user.is_premium,
                    "created_at": user.created_at,
                    "last_activity": user.last_activity,
                }
            return False, "User not found"

    @staticmethod
    async def get_user_downloads(user_id: int, limit: int = 10, offset: int = 0):
        """Get user's download history."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserDownload)
                .where(UserDownload.user_id == user_id)
                .order_by(UserDownload.downloaded_at.desc())
                .offset(offset)
                .limit(limit)
            )
            downloads = result.scalars().all()
            return True, downloads
