import os
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from dotenv import load_dotenv
from logger import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded for database configuration")

# Database configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

# Validate database configuration
for key, value in DB_CONFIG.items():
    if not value:
        error_msg = f"Missing database configuration: {key}"
        logger.error(error_msg)
        raise ValueError(error_msg)

logger.info("Database configuration validated")

# Connection pool
pool = None

def initialize_pool(min_conn=1, max_conn=10):
    """Initialize the connection pool"""
    global pool
    try:
        logger.info(f"Initializing database connection pool (min: {min_conn}, max: {max_conn})")
        pool = SimpleConnectionPool(
            min_conn,
            max_conn,
            **DB_CONFIG
        )
        logger.info("Database connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize connection pool: {str(e)}", exc_info=True)
        raise

@contextmanager
def get_connection():
    """Get a database connection from the pool"""
    global pool
    if pool is None:
        logger.info("Connection pool not initialized, initializing now")
        initialize_pool()
    
    conn = None
    try:
        conn = pool.getconn()
        logger.debug("Retrieved connection from pool")
        yield conn
    except Exception as e:
        logger.error(f"Error getting connection from pool: {str(e)}", exc_info=True)
        raise
    finally:
        if conn:
            pool.putconn(conn)
            logger.debug("Returned connection to pool")

def close_pool():
    """Close all connections in the pool"""
    global pool
    try:
        if pool:
            pool.closeall()
            logger.info("Database connection pool closed successfully")
        else:
            logger.warning("Attempted to close non-existent connection pool")
    except Exception as e:
        logger.error(f"Error closing connection pool: {str(e)}", exc_info=True)
        raise

def init_db():
    """Initialize the database by creating necessary tables"""
    logger.info("Starting database initialization")
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            # Users table
            logger.info("Creating users table")
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
            logger.info("Users table created/verified")

            # User settings table
            logger.info("Creating user_settings table")
            cur.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                download_quality VARCHAR(50) DEFAULT 'MP3_320',
                make_zip BOOLEAN DEFAULT TRUE,
                language VARCHAR(10) DEFAULT 'en',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            logger.info("User settings table created/verified")

            # User activity table
            logger.info("Creating user_activity table")
            cur.execute("""
            CREATE TABLE IF NOT EXISTS user_activity (
                activity_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                activity_type VARCHAR(50) NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            logger.info("User activity table created/verified")

            # Tracks table
            logger.info("Creating tracks table")
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
            logger.info("Tracks table created/verified")

            # Downloads table
            logger.info("Creating user_downloads table")
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
            logger.info("User downloads table created/verified")

            logger.info("Creating playlists table")
            cur.execute("""
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

            CREATE TABLE IF NOT EXISTS playlists (
                playlist_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                uuid UUID DEFAULT uuid_generate_v4() UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name)
            )
            """)
            logger.info("Playlists table created/verified")

            # Playlist tracks table (association table)
            logger.info("Creating playlist_tracks table")
            cur.execute("""
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                playlist_track_id SERIAL PRIMARY KEY,
                playlist_id INTEGER REFERENCES playlists(playlist_id) ON DELETE CASCADE,
                track_deezer_id BIGINT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            logger.info("Playlist tracks table created/verified")        
            
            conn.commit()
            logger.info("All database tables created successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create database tables: {str(e)}", exc_info=True)
            raise
        finally:
            cur.close()

def create_indexes():
    """Create indexes for better query performance"""
    logger.info("Starting index creation")
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            # Index for user downloads
            logger.info("Creating index on user_downloads(user_id)")
            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_downloads_user_id 
            ON user_downloads(user_id)
            """)

            # Index for download timestamps
            logger.info("Creating index on user_downloads(downloaded_at)")
            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_downloads_timestamp 
            ON user_downloads(downloaded_at)
            """)

            # Index for track downloads count
            logger.info("Creating index on tracks(download_count)")
            cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_tracks_downloads 
            ON tracks(download_count DESC)
            """)

            conn.commit()
            logger.info("All database indexes created successfully")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create indexes: {str(e)}", exc_info=True)
            raise
        finally:
            cur.close()

def setup_database():
    """Complete database setup"""
    try:
        logger.info("Starting complete database setup")
        init_db()
        create_indexes()
        logger.info("Database setup completed successfully")
    except Exception as e:
        logger.error(f"Database setup failed: {str(e)}", exc_info=True)
        raise
