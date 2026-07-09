import os
import asyncio
from dotenv import load_dotenv

from bale_bot.database import init_bale_models
import bale_bot.routes.command_routes
import bale_bot.routes.message_routes
import bale_bot.routes.callback_routes
from bale_bot.bot import bot
from logger import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Check for Bale bot token
TOKEN = os.getenv('BALE_BOT_TOKEN')

if not TOKEN:
    logger.error("BALE_BOT_TOKEN not found in environment variables")
    raise ValueError("BALE_BOT_TOKEN environment variable is not set")


def main():
    """Main entry point"""
    try:
        logger.info("Starting Bale music downloader bot application")
        
        @bot.on_initialize()
        async def on_startup(client):
            logger.info("Running startup tasks in bot's event loop...")
            await init_bale_models()
            logger.info("Bale database initialized")

        # Start bot
        logger.info("Starting Bale bot polling...")
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user (KeyboardInterrupt)")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}", exc_info=True)
        raise
        
    finally:
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    main()
