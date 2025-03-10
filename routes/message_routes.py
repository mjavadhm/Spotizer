from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from controllers.download_controller import DownloadController
from utils.url_validator import URLValidator
from views.message_view import MessageView
from views.music_view import MusicView
from logger import get_logger
logger = get_logger(__name__)

def setup_message_routes(dp: Router, download_controller: DownloadController):
    """Set up message route handlers"""
    router = Router()
    url_validator = URLValidator()

    @router.message(F.text)
    async def handle_message(message: Message, state: FSMContext):
        """Handle text messages - either links or search queries"""
        try:
            user_input = message.text
            chat_id = message.chat.id
            
            # Check if input is a URL
            if url_validator.is_valid_url(user_input):
                await handle_music_link(message, user_input, download_controller)
            else:
                await handle_search_query(message, user_input, state)
                
        except Exception as e:
            error_message = MessageView.get_error_message('general_error')
            await message.reply(error_message)
            raise

    async def handle_music_link(message: Message, url: str, download_controller: DownloadController):
        """Handle music download links"""
        try:
            # Send processing message
            status_message = await message.reply("⏳")
            
            # Validate URL type
            if "spotify" in url:
                if 'playlist' in url:
                    await message.reply(MessageView.get_error_message('spotify_playlist'))
                    await status_message.delete()
                    return
                    
            # Process download request
            success, result = await download_controller.process_download_request(
                user_id=message.from_user.id,
                url=url
            )
            
            if not success:
                error_message = MessageView.get_error_message('download_failed')
                await message.reply(error_message)
                await status_message.delete()
                return
            
            # Delete processing message after successful download
            await status_message.delete()
            
        except Exception as e:
            error_message = MessageView.get_error_message('download_failed')
            await message.reply(error_message)
            if 'status_message' in locals():
                await status_message.delete()
            raise

    async def handle_search_query(message: Message, query: str, state: FSMContext):
        """Handle search queries"""
        try:
            # Save search query in state
            await state.update_data(search_query=query)
            
            # Create search options keyboard
            keyboard = MessageView.get_search_keyboard(query)
            
            await message.reply(
                f"What would you like to search for '{query}'?",
                reply_markup=keyboard
            )
            
        except Exception as e:
            error_message = MessageView.get_error_message('general_error')
            await message.reply(error_message)
            raise

    @router.message(F.audio)
    async def handle_audio(message: Message):
        """Handle audio file messages"""
        await message.reply(
            "I can help you download music from Deezer and Spotify. "
            "Please send me a link to download music!"
        )

    @router.message(F.document)
    async def handle_document(message: Message):
        """Handle document messages"""
        await message.reply(
            "I can help you download music from Deezer and Spotify. "
            "Please send me a link to download music!"
        )

    @router.message(F.voice)
    async def handle_voice(message: Message):
        """Handle voice messages"""
        await message.reply(
            "I can help you download music from Deezer and Spotify. "
            "Please send me a link to download music!"
        )

    # Error handler for messages
    @router.errors
    async def message_error_handler(update: Message, exception: Exception):
        """Handle errors in message processing"""
        try:
            error_message = MessageView.get_error_message('general_error')
            await update.reply(error_message)
            
        except Exception as e:
            # If we can't send error message, log it
            logger.error(f"Error in error handler: {str(e)}")

    # Register all routes
    dp.include_router(router)
