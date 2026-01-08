import os
import asyncio
from dotenv import load_dotenv

from controllers.user_controller import UserController
from bale_bot.controllers.download_controller import BaleDownloadController
from controllers.playlist_controller import PlayListController
from database.session import init_models
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
            
            # Initialize controllers
            self.user_controller = UserController()
            self.download_controller = BaleDownloadController()
            self.playlist_controller = PlayListController()
            logger.info("Controllers initialized")
            
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

            # Initialize database
            await init_models()
            logger.info("Database initialized successfully")
            
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
        
        # Create bot instance
        bot_instance = BaleMusicDownloaderBot()
        logger.info("Bot instance created")
        
        # Initialize database synchronously first
        asyncio.run(init_models())
        logger.info("Database initialized")
        
        # Start bot (balethon's run() handles the event loop)
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
