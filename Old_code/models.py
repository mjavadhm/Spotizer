import os
import psycopg2
from psycopg2 import sql
import datetime
import logging
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Database configuration

def get_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT")
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

def create_tables():
    """Create all required tables if they don't exist"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Users table - expanded to include all Telegram user info
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username VARCHAR(255),
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            is_bot BOOLEAN DEFAULT FALSE,
            language_code VARCHAR(10),
            is_premium BOOLEAN DEFAULT FALSE,
            added_to_attachment_menu BOOLEAN DEFAULT FALSE,
            can_join_groups BOOLEAN DEFAULT TRUE,
            can_read_all_group_messages BOOLEAN DEFAULT FALSE,
            supports_inline_queries BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # User settings table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
            download_quality VARCHAR(50) DEFAULT 'MP3_320',
            make_zip BOOLEAN DEFAULT TRUE,
            language VARCHAR(10) DEFAULT 'en',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Messages table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            message_text TEXT,
            message_type VARCHAR(50),
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Tracks table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tracks (
            track_id BIGINT PRIMARY KEY,
            url TEXT NOT NULL,
            file_id TEXT,
            title VARCHAR(255),
            artist VARCHAR(255),
            album VARCHAR(255),
            duration INTEGER,
            download_count INTEGER DEFAULT 1,
            last_downloaded TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Modified user_downloads table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_downloads (
            download_id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            deezer_id BIGINT NOT NULL,
            content_type VARCHAR(20) NOT NULL, -- 'track', 'album', or 'playlist'
            file_id TEXT NOT NULL,
            quality VARCHAR(50) NOT NULL,
            url TEXT,
            title VARCHAR(255),
            artist VARCHAR(255),
            album VARCHAR(255),
            duration INTEGER,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT user_content_unique UNIQUE (user_id, deezer_id, content_type)
        )
        """)
        
        conn.commit()
        logger.info("Database tables created successfully")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating tables: {str(e)}")
        raise
    finally:
        cur.close()
        conn.close()

# User management functions
def add_user(user_id, username, first_name, last_name, **kwargs):
    """Add a new user or update existing user with all Telegram info"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
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
            # Update existing user with all fields
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
        else:
            # Add new user with all fields
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
            
            # Create default settings for new user
            cur.execute("""
            INSERT INTO user_settings (user_id)
            VALUES (%s)
            """, (user_id,))
            
        conn.commit()
        logger.info(f"User {user_id} {'updated' if result else 'added'} successfully")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error adding/updating user: {str(e)}")
        return False
    finally:
        cur.close()
        conn.close()

def get_user(user_id):
    """Get user information by user_id"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
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
        return None
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        return None
    finally:
        cur.close()
        conn.close()

# User settings functions remain the same
def update_user_settings(user_id, download_quality=None, make_zip=None, language=None):
    """Update user settings"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Build dynamic update query
        query_parts = []
        params = []
        
        if download_quality is not None:
            query_parts.append("download_quality = %s")
            params.append(download_quality)
        
        if make_zip is not None:
            query_parts.append("make_zip = %s")
            params.append(make_zip)
        
        if language is not None:
            query_parts.append("language = %s")
            params.append(language)
        
        if not query_parts:
            return False  # Nothing to update
        
        query_parts.append("updated_at = CURRENT_TIMESTAMP")
        
        query = sql.SQL("UPDATE user_settings SET {} WHERE user_id = %s").format(
            sql.SQL(", ").join(map(sql.SQL, query_parts))
        )
        
        params.append(user_id)
        cur.execute(query, params)
        
        if cur.rowcount == 0:
            # Settings don't exist, create them
            cur.execute("""
            INSERT INTO user_settings (user_id, download_quality, make_zip, language)
            VALUES (%s, %s, %s, %s)
            """, (user_id, 
                  download_quality if download_quality is not None else 'MP3_320',
                  make_zip if make_zip is not None else True,
                  language if language is not None else 'en'))
        
        conn.commit()
        logger.info(f"Settings updated for user {user_id}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating user settings: {str(e)}")
        return False
    finally:
        cur.close()
        conn.close()

def get_user_settings(user_id):
    """Get user settings"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
        SELECT download_quality, make_zip, language, updated_at
        FROM user_settings
        WHERE user_id = %s
        """, (user_id,))
        
        settings = cur.fetchone()
        if settings:
            return {
                'download_quality': settings[0],
                'make_zip': settings[1],
                'language': settings[2],
                'updated_at': settings[3]
            }
        return None
    except Exception as e:
        logger.error(f"Error getting user settings: {str(e)}")
        return None
    finally:
        cur.close()
        conn.close()

# Message logging functions remain the same
def log_message(user_id, message_text, message_type="text"):
    """Log a message from/to a user"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
        INSERT INTO messages (user_id, message_text, message_type)
        VALUES (%s, %s, %s)
        RETURNING message_id
        """, (user_id, message_text, message_type))
        
        message_id = cur.fetchone()[0]
        conn.commit()
        logger.info(f"Message logged for user {user_id}")
        return message_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Error logging message: {str(e)}")
        return None
    finally:
        cur.close()
        conn.close()

# New download functions
def add_user_download(user_id, deezer_id, content_type, file_id, quality, url=None, 
                     title=None, artist=None, album=None, duration=None, file_name=None):
    """Add a user download with the new structure"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Check if this download exists for this user
        cur.execute("""
        SELECT download_id FROM user_downloads 
        WHERE user_id = %s AND deezer_id = %s AND content_type = %s AND quality = %s
        """, (user_id, deezer_id, content_type, quality))
        
        download_exists = cur.fetchone()
        
        if download_exists:
            # Update existing download
            cur.execute("""
            UPDATE user_downloads 
            SET file_id = %s, quality = %s, url = %s, title = %s, artist = %s, 
                album = %s, duration = %s, downloaded_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND deezer_id = %s AND content_type = %s
            """, (file_id, quality, url, title, artist, album, duration, 
                 user_id, deezer_id, content_type))
        else:
            # Add new download
            cur.execute("""
            INSERT INTO user_downloads (user_id, deezer_id, content_type, file_id, quality,
                                       url, title, artist, album, duration, file_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, deezer_id, content_type, file_id, quality, 
                 url, title, artist, album, duration, file_name))
            
        conn.commit()
        logger.info(f"{content_type.capitalize()} {deezer_id} {'updated' if download_exists else 'added'} for user {user_id}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error adding/updating download: {str(e)}")
        return False
    finally:
        cur.close()
        conn.close()

def get_user_download_by_deezer_id(user_id=None, deezer_id=None, content_type=None, quality=None):
    """Get a specific download dynamically based on provided parameters"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # پایه کوئری با WHERE 1=1 برای راحتی اضافه کردن شرط‌ها
        query = sql.SQL("SELECT file_id, quality, url, title, artist, album, duration, downloaded_at, file_name FROM user_downloads WHERE deezer_id = %s")
        
        # لیست پارامترها برای جایگذاری ایمن
        params = []
        
        # اضافه کردن شرط‌ها فقط برای پارامترهای غیر None
    
        params.append(deezer_id)
        if content_type is not None:
            query += sql.SQL(" AND content_type = %s")
            params.append(content_type)
        if quality is not None:
            query += sql.SQL(" AND quality = %s")
            params.append(quality)
        
        # اجرای کوئری با پارامترها
        cur.execute(query, params)
        
        download = cur.fetchone()
        if download:
            return {
                'file_id': download[0],
                'quality': download[1],
                'url': download[2],
                'title': download[3],
                'artist': download[4],
                'album': download[5],
                'duration': download[6],
                'downloaded_at': download[7],
                'file_name': download[8]
            }
        return None
    except Exception as e:
        logger.error(f"Error getting download: {str(e)}")
        return None
    finally:
        cur.close()
        conn.close()

def get_user_downloads(user_id, limit=10, offset=0):
    """Get a user's download history with new structure"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
        SELECT deezer_id, content_type, file_id, quality, url, title, artist, album, 
               duration, downloaded_at , file_name
        FROM user_downloads
        WHERE user_id = %s
        ORDER BY downloaded_at DESC
        LIMIT %s OFFSET %s
        """, (user_id, limit, offset))
        
        downloads = []
        for row in cur.fetchall():
            downloads.append({
                'deezer_id': row[0],
                'content_type': row[1],
                'file_id': row[2],
                'quality': row[3],
                'url': row[4],
                'title': row[5],
                'artist': row[6],
                'album': row[7],
                'duration': row[8],
                'downloaded_at': row[9],
                'file_name': row[10]
            })
        return downloads
    except Exception as e:
        logger.error(f"Error getting user downloads: {str(e)}")
        return []
    finally:
        cur.close()
        conn.close()

# Initialize database tables
def init_db():
    """Initialize the database by creating all required tables"""
    try:
        create_tables()
        return True
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return False