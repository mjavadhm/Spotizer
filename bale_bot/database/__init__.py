import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

load_dotenv()

# Bale-specific database configuration
# Uses separate environment variables from Telegram bot
BALE_DB_CONFIG = {
    'user': os.getenv('BALE_DB_USER', os.getenv('DB_USER')),
    'password': os.getenv('BALE_DB_PASSWORD', os.getenv('DB_PASSWORD')),
    'host': os.getenv('BALE_DB_HOST', os.getenv('DB_HOST')),
    'port': os.getenv('BALE_DB_PORT', os.getenv('DB_PORT')),
    'database': os.getenv('BALE_DB_NAME', 'spotizer_bale')  # Default to separate DB name
}

BALE_DATABASE_URL = (
    f"postgresql+asyncpg://{BALE_DB_CONFIG['user']}:{BALE_DB_CONFIG['password']}@"
    f"{BALE_DB_CONFIG['host']}:{BALE_DB_CONFIG['port']}/{BALE_DB_CONFIG['database']}"
)

bale_async_engine = create_async_engine(BALE_DATABASE_URL, echo=True)
bale_async_session_maker = async_sessionmaker(bale_async_engine, expire_on_commit=False)

BaleBase = declarative_base()


async def init_bale_models():
    """Create all tables in the Bale database."""
    from bale_bot.database.models import BaleBase
    async with bale_async_engine.begin() as conn:
        await conn.run_sync(BaleBase.metadata.create_all)
