from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from controllers.user_controller import UserController
from controllers.playlist_controller import PlayListController
from views.message_view import MessageView
from views.playlist_view import PlaylistView
from models.message_model import MessageModel

from logger import get_logger

logger = get_logger(__name__)

def setup_command_routes(dp: Router, user_controller: UserController, playlist_controller: PlayListController):
    """Set up command route handlers"""
    router = Router()
    logger.info("Setting up command routes")

    @router.message(Command("start"))
    async def start_command(message: Message, state: FSMContext):
        """Handle /start command"""
        try:
            user = message.from_user
            user_id = user.id
            logger.info(f"Processing /start command for user {user_id}")
            
            # Get user info from message
            user_data = {
                'id': user_id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'language_code': user.language_code,
                'is_premium': getattr(user, 'is_premium', False),
                'is_bot': user.is_bot
            }
            logger.info(f"User data collected for user {user_id}: {user_data}")
            
            # Register user
            success, result = await user_controller.register_user(user_data)
            if not success:
                logger.error(f"Failed to register user {user_id}: {result}")
                sm = await message.reply("Error registering user. Please try again.")
                await MessageModel.add_message(user_id, sm)
                return
            
            logger.info(f"User {user_id} registered successfully")
            
            # Send welcome message
            welcome_message = MessageView.get_welcome_message()
            sm = await message.reply(welcome_message)
            await MessageModel.add_message(user_id, sm)
            logger.info(f"Sent welcome message to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing /start command for user {user_id}: {str(e)}", exc_info=True)
            sm = await message.reply("An error occurred. Please try again later.")
            await MessageModel.add_message(user_id, sm)
            raise

    @router.message(Command("settings"))
    async def settings_command(message: Message, state: FSMContext):
        """Handle /settings command"""
        try:
            user_id = message.from_user.id
            logger.info(f"Processing /settings command for user {user_id}")
            
            # Get user settings
            success, settings = await user_controller.get_user_settings(user_id)
            if not success:
                logger.error(f"Failed to get settings for user {user_id}: {settings}")
                sm = await message.reply("Error accessing settings. Please try again.")
                await MessageModel.add_message(user_id, sm)
                return
            
            logger.info(f"Retrieved settings for user {user_id}: {settings}")
            
            # Create settings keyboard
            keyboard = MessageView.get_settings_keyboard(settings)
            sm = await message.reply("⚙️ Your settings:", reply_markup=keyboard)
            await MessageModel.add_message(user_id, sm)
            logger.info(f"Sent settings keyboard to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing /settings command for user {user_id}: {str(e)}", exc_info=True)
            sm = await message.reply("Error accessing settings. Please try again later.")
            await MessageModel.add_message(user_id, sm)
            raise

    @router.message(Command("history"))
    async def history_command(message: Message, state: FSMContext):
        """Handle /history command"""
        try:
            user_id = message.from_user.id
            logger.info(f"Processing /history command for user {user_id}")
            
            # Get user's download history
            success, downloads = await user_controller.get_user_downloads(
                user_id,
                limit=5
            )
            
            if not success:
                logger.error(f"Failed to get download history for user {user_id}: {downloads}")
                sm = await message.reply("Error retrieving download history.")
                await MessageModel.add_message(user_id, sm)
                return
            
            logger.info(f"Retrieved {len(downloads)} download records for user {user_id}")
            
            # Format history message
            history_text = MessageView.format_download_history(downloads)
            sm = await message.reply(history_text)
            await MessageModel.add_message(user_id, sm)
            logger.info(f"Sent download history to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing /history command for user {user_id}: {str(e)}", exc_info=True)
            sm = await message.reply("Error retrieving download history.")
            await MessageModel.add_message(user_id, sm)
            raise

    @router.message(Command("help"))
    async def help_command(message: Message, state: FSMContext):
        """Handle /help command"""
        try:
            user_id = message.from_user.id
            logger.info(f"Processing /help command for user {user_id}")
            
            help_text = """🎵 *MusicDownloader Bot Help* 🎵

*Available Commands:*
/start - Start the bot and see welcome message
/settings - Customize your download preferences
/history - View your recent downloads
/help - Show this help message

*How to Use:*
1. Send a Deezer or Spotify link to download music
2. Use /settings to set your preferred:
   • Download quality (MP3 128/320 or FLAC)
   • ZIP option for albums/playlists
3. View your download history with /history

*Supported Links:*
• Deezer: Tracks, Albums, Playlists
• Spotify: Tracks, Albums (Playlists coming soon)

*Need more help?*
If you have any issues or questions, feel free to contact support."""

            sm = await message.reply(help_text, parse_mode="Markdown")
            await MessageModel.add_message(user_id, sm)
            logger.info(f"Sent help message to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing /help command for user {user_id}: {str(e)}", exc_info=True)
            sm = await message.reply("Error displaying help message.")
            await MessageModel.add_message(user_id, sm)
            raise

    @router.message(Command("about"))
    async def about_command(message: Message, state: FSMContext):
        """Handle /about command"""
        try:
            user_id = message.from_user.id
            logger.info(f"Processing /about command for user {user_id}")
            
            about_text = """🎵 *About MusicDownloader Bot* 🎵

A powerful music downloading bot that helps you get your favorite music from Deezer and Spotify.

*Features:*
• High-quality audio downloads
• Multiple format support (MP3, FLAC)
• Album and playlist support
• Custom download settings
• Download history tracking

*Version:* 1.0.0
*Developer:* @YourUsername

Thank you for using MusicDownloader Bot! 🎧"""

            sm = await message.reply(about_text, parse_mode="Markdown")
            await MessageModel.add_message(user_id, sm)
            logger.info(f"Sent about message to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing /about command for user {user_id}: {str(e)}", exc_info=True)
            sm = await message.reply("Error displaying about information.")
            await MessageModel.add_message(user_id, sm)
            raise
    
    @router.message(Command("newplaylist"))
    async def newplaylist_command(message: Message, state: FSMContext):
        """Handle /newplaylist command"""
        try:
            user_id = message.from_user.id
            logger.info(f"Processing /newplaylist command for user {user_id}")
            
            from states import PlaylistCreationStates
            from views.playlist_view import PlaylistView
            
            # Set FSM state to wait for playlist name
            await state.set_state(PlaylistCreationStates.waiting_for_name)
            message_text = PlaylistView.get_creation_message()
            sm = await message.reply(message_text)
            await MessageModel.add_message(user_id, sm)
            logger.info(f"Sent playlist creation prompt to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing /newplaylist command for user {user_id}: {str(e)}", exc_info=True)
            sm = await message.reply("Error creating playlist. Please try again.")
            await MessageModel.add_message(user_id, sm)
            raise
    
    @router.message(Command("playlists"))
    async def playlists_command(message: Message, state: FSMContext):
        try:
            user_id = message.from_user.id
            logger.info(f"Processing /playlists command for user {user_id}")

            success, playlists = await playlist_controller.get_user_playlists(user_id)
            if success:
                if playlists:
                    keyboard = PlaylistView.get_playlist_keyboard(playlists)
                    await message.reply(PlaylistView.get_choose_playlist_message(), reply_markup=keyboard)
                else:
                    await message.reply("You have no playlists.")
            else:
                await message.reply("Error retrieving playlists.")
        except Exception as e:
            logger.error(f"Error processing /playlists command for user {user_id}: {str(e)}", exc_info=True)
            await message.reply("Error displaying playlists.")

    @router.message(Command("recommend"))
    async def recommend_command(message: Message, state: FSMContext):
        """Handle /recommend command"""
        try:
            user_id = message.from_user.id
            logger.info(f"Processing /recommend command for user {user_id}")
            
            # Send initial "typing" action or message since LLM might be slow
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
            processing_msg = await message.reply("🤖 Thinking... Analyzing your taste...")
            
            from controllers.recommendation_controller import RecommendationController
            
            success, result_text = await RecommendationController.recommend_music(user_id)
            
            # Delete processing message
            await processing_msg.delete()
            
            # Send result
            sm = await message.reply(result_text, parse_mode="Markdown")
            await MessageModel.add_message(user_id, sm)
            logger.info(f"Sent recommendations to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing /recommend command for user {user_id}: {str(e)}", exc_info=True)
            sm = await message.reply("Error getting recommendations.")
            await MessageModel.add_message(user_id, sm)

    # Register all routes
    dp.include_router(router)
    logger.info("Command routes setup completed")
