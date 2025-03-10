import os
import logging
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

# Connection pool
pool = None

def initialize_pool(min_conn=1, max_conn=10):
    """Initialize the connection pool"""
    global pool
    try:
        pool = SimpleConnectionPool(
            min_conn,
            max_conn,
            **DB_CONFIG
        )
        logger.info("Database connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing connection pool: {str(e)}")
        raise

@contextmanager
def get_connection():
    """Get a database connection from the pool"""
    global pool
    if pool is None:
        initialize_pool()
    
    conn = None
    try:
        conn = pool.getconn()
        yield conn
    except Exception as e:
        logger.error(f"Error getting connection from pool: {str(e)}")
        raise
    finally:
        if conn:
            pool.putconn(conn)

def close_pool():
    """Close all connections in the pool"""
    global pool
    if pool:
        pool.closeall()
        logger.info("Database connection pool closed")

# Database initialization
def init_db():
    """Initialize the database by creating necessary tables"""
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            # Users table
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

            # User activity table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS user_activity (
                activity_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                activity_type VARCHAR(50) NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

            # Downloads table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS user_downloads (
                download_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                deezer_id BIGINT NOT NULL,
                content_type VARCHAR(20) NOT NULL,
                file_id TEXT NOT NULL,
                quality VARCHAR(50) NOT NULL,
                url TEXT,
                title VARCHAR(255),
                artist VARCHAR(255),
                album VARCHAR(255),
                duration INTEGER,
                file_name TEXT,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT user_content_unique UNIQUE (user_id, deezer_id, content_type)
            )
            """)

            conn.commit()
            logger.info("Database tables created successfully")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating database tables: {str(e)}")
            raise
        finally:
            cur.close()

# Create indexes for better performance
def create_indexes():
    """Create indexes for better query performance"""
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            # Index for user downloads
            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_downloads_user_id 
            ON user_downloads(user_id)
            """)

            # Index for download timestamps
            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_downloads_timestamp 
            ON user_downloads(downloaded_at)
            """)

            # Index for track downloads count
            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_tracks_downloads 
            ON tracks(download_count DESC)
            """)

            conn.commit()
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating indexes: {str(e)}")
            raise
        finally:
            cur.close()

def setup_database():
    """Complete database setup"""
    try:
        init_db()
        create_indexes()
        logger.info("Database setup completed successfully")
    except Exception as e:
        logger.error(f"Database setup failed: {str(e)}")
        raise
