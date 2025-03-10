from typing import Dict, Optional, Any
from datetime import datetime
from database.connection import get_connection
from logger import get_logger

logger = get_logger(__name__)

class UserModel:
    def __init__(self):
        """Initialize UserModel"""
        self.default_settings = {
            'download_quality': 'MP3_320',
            'make_zip': True,
            'language': 'en'
        }

    def add_user(self, user_id: int, username: str = None, first_name: str = None, 
                 last_name: str = None, **kwargs) -> bool:
        """Add a new user or update existing user with all Telegram info"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # Check if user exists
                    cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                    result = cur.fetchone()
                    
                    # Extract additional Telegram user fields
                    is_bot = kwargs.get('is_bot', False)
                    language_code = kwargs.get('language_code')
                    is_premium = kwargs.get('is_premium', False)
                    added_to_attachment_menu = kwargs.get('added_to_attachment_menu', False)
                    can_join_groups = kwargs.get('can_join_groups', True)
                    can_read_all_group_messages = kwargs.get('can_read_all_group_messages', False)
                    supports_inline_queries = kwargs.get('supports_inline_queries', False)
                    
                    if result:
                        # Update existing user
                        cur.execute("""
                        UPDATE users 
                        SET username = %s, first_name = %s, last_name = %s,
                            is_bot = %s, language_code = %s, is_premium = %s,
                            added_to_attachment_menu = %s, can_join_groups = %s,
                            can_read_all_group_messages = %s, supports_inline_queries = %s,
                            last_activity = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                        """, (
                            username, first_name, last_name, is_bot, language_code, is_premium,
                            added_to_attachment_menu, can_join_groups, can_read_all_group_messages,
                            supports_inline_queries, user_id
                        ))
                        logger.info(f"Updated user record for user {user_id}")
                    else:
                        # Add new user
                        cur.execute("""
                        INSERT INTO users (
                            user_id, username, first_name, last_name, is_bot, language_code,
                            is_premium, added_to_attachment_menu, can_join_groups,
                            can_read_all_group_messages, supports_inline_queries
                        ) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            user_id, username, first_name, last_name, is_bot, language_code,
                            is_premium, added_to_attachment_menu, can_join_groups,
                            can_read_all_group_messages, supports_inline_queries
                        ))
                        logger.info(f"Added new user record for user {user_id}")
                        
                        # Create default settings for new user
                        self.create_default_settings(user_id)
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to add/update user: {str(e)}", exc_info=True)
            return False

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information by user_id"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                    SELECT u.user_id, u.username, u.first_name, u.last_name, u.is_bot,
                           u.language_code, u.is_premium, u.added_to_attachment_menu,
                           u.can_join_groups, u.can_read_all_group_messages, u.supports_inline_queries,
                           u.created_at, u.last_activity,
                           s.download_quality, s.make_zip, s.language
                    FROM users u
                    LEFT JOIN user_settings s ON u.user_id = s.user_id
                    WHERE u.user_id = %s
                    """, (user_id,))
                    
                    user = cur.fetchone()
                    if user:
                        logger.info(f"Retrieved user record for user {user_id}")
                        return {
                            'user_id': user[0],
                            'username': user[1],
                            'first_name': user[2],
                            'last_name': user[3],
                            'is_bot': user[4],
                            'language_code': user[5],
                            'is_premium': user[6],
                            'added_to_attachment_menu': user[7],
                            'can_join_groups': user[8],
                            'can_read_all_group_messages': user[9],
                            'supports_inline_queries': user[10],
                            'created_at': user[11],
                            'last_activity': user[12],
                            'settings': {
                                'download_quality': user[13],
                                'make_zip': user[14],
                                'language': user[15]
                            }
                        }
                    logger.info(f"No user record found for user {user_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to retrieve user: {str(e)}", exc_info=True)
            return None

    def update_settings(self, user_id: int, **settings) -> bool:
        """Update user settings"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # Build dynamic update query based on provided settings
                    update_fields = []
                    params = []
                    
                    for key, value in settings.items():
                        if value is not None:
                            update_fields.append(f"{key} = %s")
                            params.append(value)
                    
                    if not update_fields:
                        logger.info(f"No settings to update for user {user_id}")
                        return False  # Nothing to update
                    
                    update_fields.append("updated_at = CURRENT_TIMESTAMP")
                    
                    # Construct and execute query
                    query = f"""
                    UPDATE user_settings 
                    SET {', '.join(update_fields)}
                    WHERE user_id = %s
                    """
                    params.append(user_id)
                    
                    cur.execute(query, params)
                    
                    if cur.rowcount == 0:
                        # Settings don't exist, create them
                        logger.info(f"Creating default settings for user {user_id} with overrides")
                        self.create_default_settings(user_id, **settings)
                    else:
                        logger.info(f"Updated settings for user {user_id}")
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to update user settings: {str(e)}", exc_info=True)
            return False

    def get_settings(self, user_id: int) -> Dict[str, Any]:
        """Get user settings"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                    SELECT download_quality, make_zip, language, updated_at
                    FROM user_settings
                    WHERE user_id = %s
                    """, (user_id,))
                    
                    settings = cur.fetchone()
                    if settings:
                        logger.info(f"Retrieved settings for user {user_id}")
                        return {
                            'download_quality': settings[0],
                            'make_zip': settings[1],
                            'language': settings[2],
                            'updated_at': settings[3]
                        }
                    
                    # If no settings found, create default settings and return them
                    logger.info(f"No settings found for user {user_id}, creating defaults")
                    self.create_default_settings(user_id)
                    return self.default_settings.copy()
                    
        except Exception as e:
            logger.error(f"Failed to retrieve user settings: {str(e)}", exc_info=True)
            # Return default settings in case of error
            return self.default_settings.copy()

    def create_default_settings(self, user_id: int, **override_settings) -> bool:
        """Create default settings for a new user"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # Merge default settings with any overrides
                    settings = self.default_settings.copy()
                    settings.update(override_settings)
                    
                    cur.execute("""
                    INSERT INTO user_settings (user_id, download_quality, make_zip, language)
                    VALUES (%s, %s, %s, %s)
                    """, (
                        user_id,
                        settings['download_quality'],
                        settings['make_zip'],
                        settings['language']
                    ))
                    
                    conn.commit()
                    logger.info(f"Created default settings for user {user_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to create default settings: {str(e)}", exc_info=True)
            return False

    def log_activity(self, user_id: int, activity_type: str, details: str = None) -> bool:
        """Log user activity"""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                    INSERT INTO user_activity (user_id, activity_type, details)
                    VALUES (%s, %s, %s)
                    """, (user_id, activity_type, details))
                    
                    conn.commit()
                    logger.info(f"Logged activity for user {user_id}: {activity_type}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to log user activity: {str(e)}", exc_info=True)
            return False

    def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """Alias for get_settings for backward compatibility"""
        return self.get_settings(user_id)
