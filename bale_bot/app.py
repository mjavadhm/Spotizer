import os
import asyncio
from dotenv import load_dotenv

from bale_bot.controllers.user_controller import BaleUserController
from bale_bot.controllers.download_controller import BaleDownloadController
from bale_bot.controllers.playlist_controller import BalePlaylistController
from bale_bot.database import init_bale_models
from bale_bot.routes.command_routes import setup_command_routes
from bale_bot.routes.message_routes import setup_message_routes
from bale_bot.routes.callback_routes import setup_callback_routes
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


class BaleMusicDownloaderBot:
    def __init__(self):
        """Initialize the Bale bot with all necessary components"""
        try:
            logger.info("Initializing BaleMusicDownloaderBot")
            
            # Initialize Bale-specific controllers
            self.user_controller = BaleUserController()
            self.download_controller = BaleDownloadController()
            self.playlist_controller = BalePlaylistController()
            logger.info("Bale controllers initialized")
            
            # Set up routes
            self._setup_routes()
            
            logger.info("Bot initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {str(e)}", exc_info=True)
            raise

    def _setup_routes(self):
        """Set up all route handlers"""
        try:
            logger.info("Setting up route handlers")
            
            # Set up command routes (start, settings, history)
            setup_command_routes(self.user_controller, self.playlist_controller)
            logger.info("Command routes configured")
            
            # Set up message routes (link processing, search)
            setup_message_routes(self.download_controller)
            logger.info("Message routes configured")
            
            # Set up callback routes (buttons, pagination)
            setup_callback_routes(self.user_controller, self.download_controller, self.playlist_controller)
            logger.info("Callback routes configured")
            
            logger.info("All routes set up successfully")
            
        except Exception as e:
            logger.error(f"Failed to set up routes: {str(e)}", exc_info=True)
            raise

    async def start(self):
        """Start the bot"""
        try:
            logger.info("Starting bot initialization")

            # Initialize Bale-specific database
            await init_bale_models()
            logger.info("Bale database initialized successfully")
            
            # Start the bot (balethon uses run() method)
            logger.info("Starting Bale bot...")
            bot.run()
            
        except Exception as e:
            logger.error(f"Failed to start bot: {str(e)}", exc_info=True)
            raise


def main():
    """Main entry point"""
    try:
        logger.info("Starting Bale music downloader bot application")
        
        # Set up all routes before running
        bot_instance = BaleMusicDownloaderBot()
        logger.info("Bot instance created")
        
        # Initialize Bale-specific database synchronously first
        asyncio.run(init_bale_models())
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
