import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.session.aiohttp import AiohttpSession

from controllers.user_controller import UserController
from controllers.download_controller import DownloadController
from controllers.playlist_controller import PlayListController
from database.connection import setup_database
from routes.command_routes import setup_command_routes
from routes.message_routes import setup_message_routes
from routes.callback_routes import setup_callback_routes
from bot import bot
from logger import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Bot configuration
API_BASE_URL = 'http://89.22.236.107:9097'
TOKEN = os.getenv('BOT_TOKEN')

if not TOKEN:
    logger.error("Bot token not found in environment variables")
    raise ValueError("BOT_TOKEN environment variable is not set")

class MusicDownloaderBot:
    def __init__(self):
        """Initialize the bot with all necessary components"""
        try:
            logger.info("Initializing MusicDownloaderBot")
            
            # Initialize bot and dispatcher
            self.bot = bot
            self.dp = Dispatcher()
            logger.info("Bot and dispatcher initialized")
            
            # Initialize controllers
            self.user_controller = UserController()
            self.download_controller = DownloadController()
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
            setup_command_routes(self.dp, self.user_controller, self.playlist_controller)
            logger.info("Command routes configured")
            
            # Set up message routes (link processing, search)
            setup_message_routes(self.dp, self.download_controller)
            logger.info("Message routes configured")
            
            # Set up callback routes (buttons, pagination)
            setup_callback_routes(self.dp, self.user_controller, self.download_controller, self.playlist_controller)
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
            setup_database()
            logger.info("Database initialized successfully")
            
            # Start polling
            logger.info("Starting bot polling...")
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            logger.error(f"Failed to start bot: {str(e)}", exc_info=True)
            raise

async def main():
    """Main entry point"""
    bot_instance = None
    try:
        logger.info("Starting main application")
        
        # Create and start bot
        bot_instance = MusicDownloaderBot()
        logger.info("Bot instance created")
        
        await bot_instance.start()
        logger.info("Bot started successfully")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}", exc_info=True)
        raise
        
    finally:
        # Ensure proper cleanup
        if bot_instance:
            try:
                await bot_instance.bot.session.close()
                logger.info("Bot session closed successfully")
            except Exception as e:
                logger.error(f"Error during session cleanup: {str(e)}", exc_info=True)

if __name__ == "__main__":
    try:
        logger.info("Application starting")
        asyncio.run(main())
        logger.info("Application completed normally")
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user (KeyboardInterrupt)")
        
    except Exception as e:
        logger.error(f"Unexpected application error: {str(e)}", exc_info=True)
        
    finally:
        try:
            # Additional cleanup if needed
            logger.info("Performing final cleanup")
            # Add any additional cleanup code here
            
        except Exception as e:
            logger.error(f"Error during final cleanup: {str(e)}", exc_info=True)
            
        finally:
            logger.info("Application shutdown complete")
