from bale_bot.controllers.download_controller import BaleDownloadController
from bale_bot.controllers.playlist_controller import BalePlaylistController
from utils.url_validator import URLValidator
from bale_bot.views.message_view import MessageView
from bale_bot.views.music_view import MusicView
from bale_bot.views.playlist_view import PlaylistView
from bale_bot.bot import bot
from logger import get_logger

logger = get_logger(__name__)


def setup_message_routes(download_controller: BaleDownloadController):
    """Set up message route handlers for Bale bot"""
    url_validator = URLValidator()
    playlist_controller = BalePlaylistController()
    logger.info("Setting up message routes for Bale")

    @bot.on_message(lambda message: message.text and not message.text.startswith("/"))
    async def handle_text_message(message):
        """Handle text messages - either links or search queries"""
        try:
            user_input = message.text
            chat_id = message.chat.id
            user_id = message.from_user.id
            logger.info(f"Handling message from user {user_id} in chat {chat_id}: {user_input}")
            
            # Check if input is a URL
            if url_validator.is_valid_url(user_input):
                logger.info(f"Processing URL from user {user_id}: {user_input}")
                await handle_music_link(message, user_input, download_controller)
            else:
                logger.info(f"Processing search query from user {user_id}: {user_input}")
                await handle_search_query(message, user_input)
                
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            error_message = MessageView.get_error_message('general_error')
            await message.reply(error_message)

    async def handle_music_link(message, url: str, download_controller: BaleDownloadController):
        """Handle music download links"""
        status_message = None
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
                    await message.reply(MessageView.get_error_message('spotify_playlist'))
                    if status_message:
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
                # Show the actual error message if it's user-friendly, otherwise show generic
                error_message = result if result and isinstance(result, str) else MessageView.get_error_message('download_failed')
                await message.reply(error_message)
                if status_message:
                    await status_message.delete()
                return
            
            logger.info(f"Download completed successfully for user {user_id}")
            # Delete processing message after successful download
            if status_message:
                await status_message.delete()
            
        except Exception as e:
            logger.error(f"Error handling music link for user {user_id}: {str(e)}", exc_info=True)
            error_message = MessageView.get_error_message('download_failed')
            await message.reply(error_message)
            if status_message:
                try:
                    await status_message.delete()
                except:
                    pass

    async def handle_search_query(message, query: str):
        """Handle search queries"""
        try:
            user_id = message.from_user.id
            logger.info(f"Processing search query for user {user_id}: {query}")
            
            # Create search options keyboard
            keyboard = MessageView.get_search_keyboard(query)
            logger.info(f"Created search keyboard for user {user_id}")
            
            await message.reply(
                f"What would you like to search for '{query}'?",
                reply_markup=keyboard
            )
            logger.info(f"Sent search options to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error handling search query for user {user_id}: {str(e)}", exc_info=True)
            error_message = MessageView.get_error_message('general_error')
            await message.reply(error_message)

    @bot.on_message(lambda message: message.audio is not None)
    async def handle_audio(message):
        """Handle audio file messages"""
        user_id = message.from_user.id
        logger.info(f"Received audio message from user {user_id}")
        await message.reply(
            "I can help you download music from Deezer and Spotify. "
            "Please send me a link to download music!"
        )
        logger.info(f"Sent help message to user {user_id}")

    @bot.on_message(lambda message: message.document is not None)
    async def handle_document(message):
        """Handle document messages"""
        user_id = message.from_user.id
        logger.info(f"Received document message from user {user_id}")
        await message.reply(
            "I can help you download music from Deezer and Spotify. "
            "Please send me a link to download music!"
        )
        logger.info(f"Sent help message to user {user_id}")

    @bot.on_message(lambda message: message.voice is not None)
    async def handle_voice(message):
        """Handle voice messages"""
        user_id = message.from_user.id
        logger.info(f"Received voice message from user {user_id}")
        await message.reply(
            "I can help you download music from Deezer and Spotify. "
            "Please send me a link to download music!"
        )
        logger.info(f"Sent help message to user {user_id}")

    logger.info("Message routes setup completed for Bale")
