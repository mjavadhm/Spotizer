from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from controllers.download_controller import DownloadController
from utils.url_validator import URLValidator
from views.message_view import MessageView
from views.music_view import MusicView
from models.message_model import MessageModel
from logger import get_logger

logger = get_logger(__name__)

def setup_message_routes(dp: Router, download_controller: DownloadController):
    """Set up message route handlers"""
    router = Router()
    url_validator = URLValidator()
    logger.info("Setting up message routes")
    message_model = MessageModel()
    @router.message(F.text)
    async def handle_message(message: Message, state: FSMContext):
        """Handle text messages - either links or search queries"""
        try:
            user_input = message.text
            chat_id = message.chat.id
            user_id = message.from_user.id
            message_model.add_message(user_id, message)
            logger.info(f"Handling message from user {user_id} in chat {chat_id}: {user_input}")
            
            # Check if input is a URL
            if url_validator.is_valid_url(user_input):
                logger.info(f"Processing URL from user {user_id}: {user_input}")
                await handle_music_link(message, user_input, download_controller)
            else:
                logger.info(f"Processing search query from user {user_id}: {user_input}")
                await handle_search_query(message, user_input, state)
                
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            error_message = MessageView.get_error_message('general_error')
            sm = await message.reply(error_message)
            message_model.add_message(user_id, sm)
            raise

    async def handle_music_link(message: Message, url: str, download_controller: DownloadController):
        """Handle music download links"""
        try:
            user_id = message.from_user.id
            logger.info(f"Processing music link for user {user_id}: {url}")
            
            # Send processing message
            status_message = await message.reply("⏳")
            logger.info(f"Sent processing status message to user {user_id}")
            
            # Validate URL type
            if "spotify" in url:
                if 'playlist' in url:
                    logger.warning(f"Spotify playlist not supported: {url}")
                    sm = await message.reply(MessageView.get_error_message('spotify_playlist'))
                    message_model.add_message(user_id, sm)
                    await status_message.delete()
                    return
                    
            # Process download request
            logger.info(f"Starting download process for user {user_id}")
            success, result = await download_controller.process_download_request(
                user_id=user_id,
                url=url
            )
            
            if not success:
                logger.error(f"Download failed for user {user_id}: {result}")
                error_message = MessageView.get_error_message('download_failed')
                sm = await message.reply(error_message)
                message_model.add_message(user_id, sm)
                await status_message.delete()
                return
            
            logger.info(f"Download completed successfully for user {user_id}")
            # Delete processing message after successful download
            await status_message.delete()
            
        except Exception as e:
            logger.error(f"Error handling music link for user {user_id}: {str(e)}", exc_info=True)
            error_message = MessageView.get_error_message('download_failed')
            sm = await message.reply(error_message)
            message_model.add_message(user_id, sm)
            if 'status_message' in locals():
                await status_message.delete()
            raise

    async def handle_search_query(message: Message, query: str, state: FSMContext):
        """Handle search queries"""
        try:
            user_id = message.from_user.id
            logger.info(f"Processing search query for user {user_id}: {query}")
            
            # Save search query in state
            await state.update_data(search_query=query)
            logger.info(f"Saved search query to state for user {user_id}")
            
            # Create search options keyboard
            keyboard = MessageView.get_search_keyboard(query)
            logger.info(f"Created search keyboard for user {user_id}")
            
            sm = await message.reply(
                f"What would you like to search for '{query}'?",
                reply_markup=keyboard
            )
            message_model.add_message(user_id, sm)
            logger.info(f"Sent search options to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling search query for user {user_id}: {str(e)}", exc_info=True)
            error_message = MessageView.get_error_message('general_error')
            sm = await message.reply(error_message)
            raise

    @router.message(F.audio)
    async def handle_audio(message: Message):
        """Handle audio file messages"""
        user_id = message.from_user.id
        message_model.add_message(user_id, message)
        logger.info(f"Received audio message from user {user_id}")
        sm = await message.reply(
            "I can help you download music from Deezer and Spotify. "
            "Please send me a link to download music!"
        )
        message_model.add_message(user_id, sm)
        logger.info(f"Sent help message to user {user_id}")

    @router.message(F.document)
    async def handle_document(message: Message):
        """Handle document messages"""
        user_id = message.from_user.id
        message_model.add_message(user_id, message)
        logger.info(f"Received document message from user {user_id}")
        sm = await message.reply(
            "I can help you download music from Deezer and Spotify. "
            "Please send me a link to download music!"
        )
        message_model.add_message(user_id, sm)
        logger.info(f"Sent help message to user {user_id}")

    @router.message(F.voice)
    async def handle_voice(message: Message):
        """Handle voice messages"""
        user_id = message.from_user.id
        message_model.add_message(user_id, message)
        logger.info(f"Received voice message from user {user_id}")
        sm = await message.reply(
            "I can help you download music from Deezer and Spotify. "
            "Please send me a link to download music!"
        )
        message_model.add_message(user_id, sm)
        logger.info(f"Sent help message to user {user_id}")

    # Error handler for messages
    @router.errors
    async def message_error_handler(update: Message, exception: Exception):
        """Handle errors in message processing"""
        try:
            user_id = update.from_user.id if update.from_user else "Unknown"
            logger.error(f"Error processing message from user {user_id}: {str(exception)}", exc_info=True)
            error_message = MessageView.get_error_message('general_error')
            await update.reply(error_message)
            logger.info(f"Sent error message to user {user_id}")
            
        except Exception as e:
            # If we can't send error message, log it
            logger.error(f"Critical error in error handler: {str(e)}", exc_info=True)

    # Register all routes
    dp.include_router(router)
    logger.info("Message routes setup completed")
