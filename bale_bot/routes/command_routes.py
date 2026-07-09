from bale_bot.controllers.user_controller import BaleUserController
from bale_bot.controllers.playlist_controller import BalePlaylistController
from bale_bot.views.message_view import MessageView
from bale_bot.views.playlist_view import PlaylistView
from bale_bot.bot import bot
from logger import get_logger

logger = get_logger(__name__)


user_controller = BaleUserController()
playlist_controller = BalePlaylistController()
logger.info("Setting up command routes for Bale")

@bot.on_command(name="start")
async def start_command(*, message):
    """Handle /start command"""
    try:
        user = message.author
        user_id = user.id
        logger.info(f"Processing /start command for user {user_id}")
        
        # Get user info from message
        user_data = {
            'id': user_id,
            'username': getattr(user, 'username', None),
            'first_name': getattr(user, 'first_name', None),
            'last_name': getattr(user, 'last_name', None),
            'language_code': getattr(user, 'language_code', None),
            'is_bot': getattr(user, 'is_bot', False)
        }
        logger.info(f"User data collected for user {user_id}: {user_data}")
        
        # Register user
        success, result = await user_controller.register_user(user_data)
        if not success:
            logger.error(f"Failed to register user {user_id}: {result}")
            await message.reply("Error registering user. Please try again.")
            return
        
        logger.info(f"User {user_id} registered successfully")
        
        # Send welcome message
        welcome_message = MessageView.get_welcome_message()
        await message.reply(welcome_message)
        logger.info(f"Sent welcome message to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing /start command: {str(e)}", exc_info=True)
        await message.reply("An error occurred. Please try again later.")

@bot.on_command(name="settings")
async def settings_command(*, message):
    """Handle /settings command"""
    try:
        user_id = message.author.id
        logger.info(f"Processing /settings command for user {user_id}")
        
        # Get user settings
        success, settings = await user_controller.get_user_settings(user_id)
        if not success:
            logger.error(f"Failed to get settings for user {user_id}: {settings}")
            await message.reply("Error accessing settings. Please try again.")
            return
        
        logger.info(f"Retrieved settings for user {user_id}: {settings}")
        
        # Create settings keyboard
        keyboard = MessageView.get_settings_keyboard(settings)
        await message.reply("⚙️ Your settings:", reply_markup=keyboard)
        logger.info(f"Sent settings keyboard to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing /settings command: {str(e)}", exc_info=True)
        await message.reply("Error accessing settings. Please try again later.")

@bot.on_command(name="history")
async def history_command(*, message):
    """Handle /history command"""
    try:
        user_id = message.author.id
        logger.info(f"Processing /history command for user {user_id}")
        
        # Get user's download history
        success, downloads = await user_controller.get_user_downloads(user_id, limit=5)
        
        if not success:
            logger.error(f"Failed to get download history for user {user_id}: {downloads}")
            await message.reply("Error retrieving download history.")
            return
        
        logger.info(f"Retrieved {len(downloads)} download records for user {user_id}")
        
        # Format history message
        history_text = MessageView.format_download_history(downloads)
        await message.reply(history_text)
        logger.info(f"Sent download history to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing /history command: {str(e)}", exc_info=True)
        await message.reply("Error retrieving download history.")

@bot.on_command(name="help")
async def help_command(*, message):
    """Handle /help command"""
    try:
        user_id = message.author.id
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

        await message.reply(help_text)
        logger.info(f"Sent help message to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing /help command: {str(e)}", exc_info=True)
        await message.reply("Error displaying help message.")

@bot.on_command(name="about")
async def about_command(*, message):
    """Handle /about command"""
    try:
        user_id = message.author.id
        logger.info(f"Processing /about command for user {user_id}")
        
        about_text = """🎵 *About MusicDownloader Bot* 🎵

A powerful music downloading bot that helps you get your favorite music from Deezer and Spotify.

*Features:*
• High-quality audio downloads
• Multiple format support (MP3, FLAC)
• Album and playlist support
• Custom download settings
• Download history tracking

*Version:* 1.0.0 (Bale Edition)

Thank you for using MusicDownloader Bot! 🎧"""

        await message.reply(about_text)
        logger.info(f"Sent about message to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing /about command: {str(e)}", exc_info=True)
        await message.reply("Error displaying about information.")

@bot.on_command(name="newplaylist")
async def newplaylist_command(*, message):
    """Handle /newplaylist command"""
    try:
        user_id = message.author.id
        logger.info(f"Processing /newplaylist command for user {user_id}")
        
        # For Bale, we'll use a simpler approach without complex FSM
        # Just ask user to send playlist name
        message_text = PlaylistView.get_creation_message()
        await message.reply(message_text)
        logger.info(f"Sent playlist creation prompt to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing /newplaylist command: {str(e)}", exc_info=True)
        await message.reply("Error creating playlist. Please try again.")

@bot.on_command(name="playlists")
async def playlists_command(*, message):
    try:
        user_id = message.author.id
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
        logger.error(f"Error processing /playlists command: {str(e)}", exc_info=True)
        await message.reply("Error displaying playlists.")

@bot.on_command(name="recommend")
async def recommend_command(*, message):
    """Handle /recommend command"""
    try:
        user_id = message.author.id
        logger.info(f"Processing /recommend command for user {user_id}")
        
        # Send initial message since LLM might be slow
        processing_msg = await message.reply("🤖 Thinking... Analyzing your taste...")
        
        from controllers.recommendation_controller import RecommendationController
        
        success, result_text = await RecommendationController.recommend_music(user_id)
        
        # Send result
        await message.reply(result_text)
        logger.info(f"Sent recommendations to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing /recommend command: {str(e)}", exc_info=True)
        await message.reply("Error getting recommendations.")

logger.info("Command routes setup completed for Bale")
