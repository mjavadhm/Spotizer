import logging
from models.user_model import UserModel
from models.download_model import DownloadModel
from utils.url_validator import validate_settings

logger = logging.getLogger(__name__)

class UserController:
    def __init__(self):
        self.user_model = UserModel()
        self.download_model = DownloadModel()

    async def register_user(self, user_data):
        """Register or update user information"""
        try:
            user_id = user_data.get('id')
            if not user_id:
                return False, "Invalid user data: Missing user ID"

            user_info = {
                'user_id': user_id,
                'username': user_data.get('username'),
                'first_name': user_data.get('first_name'),
                'last_name': user_data.get('last_name'),
                'language_code': user_data.get('language_code'),
                'is_premium': user_data.get('is_premium', False),
                'is_bot': user_data.get('is_bot', False)
            }

            success = self.user_model.add_user(**user_info)
            if success:
                return True, "User registered successfully"
            return False, "Failed to register user"

        except Exception as e:
            logger.error(f"User registration error: {str(e)}")
            return False, "An error occurred during user registration"

    async def update_user_settings(self, user_id, settings):
        """Update user settings"""
        try:
            # Validate settings
            valid, message = validate_settings(settings)
            if not valid:
                return False, message

            # Update settings in database
            success = self.user_model.update_settings(
                user_id,
                download_quality=settings.get('download_quality'),
                make_zip=settings.get('make_zip'),
                language=settings.get('language')
            )

            if success:
                return True, "Settings updated successfully"
            return False, "Failed to update settings"

        except Exception as e:
            logger.error(f"Settings update error: {str(e)}")
            return False, "An error occurred while updating settings"

    async def get_user_settings(self, user_id):
        """Get user settings"""
        try:
            settings = self.user_model.get_settings(user_id)
            if settings:
                return True, settings
            return False, "Settings not found"

        except Exception as e:
            logger.error(f"Error fetching settings: {str(e)}")
            return False, "An error occurred while retrieving settings"

    async def get_user_info(self, user_id):
        """Get user information"""
        try:
            user_info = self.user_model.get_user(user_id)
            if user_info:
                return True, user_info
            return False, "User not found"

        except Exception as e:
            logger.error(f"Error fetching user info: {str(e)}")
            return False, "An error occurred while retrieving user information"

    async def get_user_downloads(self, user_id: int, limit: int = 10, offset: int = 0):
        """Get user's download history"""
        try:
            downloads = self.download_model.get_user_downloads(user_id, limit, offset)
            return True, downloads
        except Exception as e:
            logger.error(f"Error getting user downloads: {str(e)}")
            return False, "An error occurred while retrieving download history"
