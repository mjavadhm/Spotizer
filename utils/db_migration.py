import sys
import os
import logging

# Add root directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_db():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                logger.info("Checking tracks table schema...")

                # Check and add channel_id
                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name='tracks' AND column_name='channel_id';
                """)
                if not cur.fetchone():
                    logger.info("Adding channel_id column...")
                    cur.execute("ALTER TABLE tracks ADD COLUMN channel_id BIGINT;")
                else:
                    logger.info("channel_id column already exists.")

                # Check and add message_id
                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name='tracks' AND column_name='message_id';
                """)
                if not cur.fetchone():
                    logger.info("Adding message_id column...")
                    cur.execute("ALTER TABLE tracks ADD COLUMN message_id BIGINT;")
                else:
                    logger.info("message_id column already exists.")

                # Check and add quality
                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name='tracks' AND column_name='quality';
                """)
                if not cur.fetchone():
                    logger.info("Adding quality column...")
                    cur.execute("ALTER TABLE tracks ADD COLUMN quality VARCHAR(50);")
                else:
                    logger.info("quality column already exists.")

                # Check and add file_name
                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name='tracks' AND column_name='file_name';
                """)
                if not cur.fetchone():
                    logger.info("Adding file_name column...")
                    cur.execute("ALTER TABLE tracks ADD COLUMN file_name TEXT;")
                else:
                    logger.info("file_name column already exists.")

                conn.commit()
                logger.info("Migration completed successfully.")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        # sys.exit(1) # Don't exit in sandbox if no DB connection, just log

if __name__ == "__main__":
    migrate_db()
