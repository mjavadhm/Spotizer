import os
import logging
from dotenv import load_dotenv
from balethon import Client

load_dotenv()

logger = logging.getLogger(__name__)

try:
    TOKEN = os.getenv('BALE_BOT_TOKEN')
    if not TOKEN:
        raise ValueError("BALE_BOT_TOKEN environment variable is not set")
    
    bot = Client(TOKEN)
    logger.info("Bale bot client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Bale bot: {e}")
    raise
