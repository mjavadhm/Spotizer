import os
import asyncio
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.session.aiohttp import AiohttpSession

from controllers.user_controller import UserController
from controllers.download_controller import DownloadController
from database.connection import setup_database
from routes.command_routes import setup_command_routes
from routes.message_routes import setup_message_routes
from routes.callback_routes import setup_callback_routes

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(filename)s:%(lineno)d - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Bot configuration
API_BASE_URL = 'http://89.22.236.107:9097'
TOKEN = os.getenv('BOT_TOKEN')

class MusicDownloaderBot:
    def __init__(self):
        """Initialize the bot with all necessary components"""
        # Set up API server and session
        self.api_server = TelegramAPIServer.from_base(base=API_BASE_URL)
        self.session = AiohttpSession(api=self.api_server)
        
        # Initialize bot and dispatcher
        self.bot = Bot(token=TOKEN, session=self.session)
        self.dp = Dispatcher()
        
        # Initialize controllers
        self.user_controller = UserController()
        self.download_controller = DownloadController()
        
        # Set up routes
        self._setup_routes()
        
        logger.info("Bot initialized successfully")

    def _setup_routes(self):
        """Set up all route handlers"""
        # Set up command routes (start, settings, history)
        setup_command_routes(self.dp, self.user_controller)
        
        # Set up message routes (link processing, search)
        setup_message_routes(self.dp, self.download_controller)
        
        # Set up callback routes (buttons, pagination)
        setup_callback_routes(self.dp, self.user_controller, self.download_controller)
        
        logger.info("Routes set up successfully")

    async def start(self):
        """Start the bot"""
        try:
            # Initialize database
            setup_database()
            logger.info("Database initialized")
            
            # Start polling
            logger.info("Starting bot polling...")
            await self.dp.start_polling(self.bot)
            
        except Exception as e:
            logger.error(f"Error starting bot: {str(e)}")
            raise

async def main():
    """Main entry point"""
    try:
        # Create and start bot
        bot = MusicDownloaderBot()
        await bot.start()
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise
    finally:
        # Ensure proper cleanup
        if 'bot' in locals():
            await bot.bot.session.close()
            logger.info("Bot session closed")

if __name__ == "__main__":
    try:
        # Run the bot
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        logger.info("Bot shutdown complete")
