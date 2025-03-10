from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from controllers.user_controller import UserController
from views.message_view import MessageView

def setup_command_routes(dp: Router, user_controller: UserController):
    """Set up command route handlers"""
    router = Router()

    @router.message(Command("start"))
    async def start_command(message: Message, state: FSMContext):
        """Handle /start command"""
        try:
            # Get user info from message
            user = message.from_user
            user_data = {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'language_code': user.language_code,
                'is_premium': getattr(user, 'is_premium', False),
                'is_bot': user.is_bot
            }
            
            # Register user
            success, result = await user_controller.register_user(user_data)
            if not success:
                await message.reply("Error registering user. Please try again.")
                return
            
            # Send welcome message
            welcome_message = MessageView.get_welcome_message()
            await message.reply(welcome_message)
            
        except Exception as e:
            await message.reply("An error occurred. Please try again later.")
            raise

    @router.message(Command("settings"))
    async def settings_command(message: Message, state: FSMContext):
        """Handle /settings command"""
        try:
            # Get user settings
            success, settings = await user_controller.get_user_settings(message.from_user.id)
            if not success:
                await message.reply("Error accessing settings. Please try again.")
                return
            
            # Create settings keyboard
            keyboard = MessageView.get_settings_keyboard(settings)
            await message.reply("⚙️ Your settings:", reply_markup=keyboard)
            
        except Exception as e:
            await message.reply("Error accessing settings. Please try again later.")
            raise

    @router.message(Command("history"))
    async def history_command(message: Message, state: FSMContext):
        """Handle /history command"""
        try:
            # Get user's download history
            success, downloads = await user_controller.get_user_downloads(
                message.from_user.id,
                limit=5
            )
            
            if not success:
                await message.reply("Error retrieving download history.")
                return
            
            # Format history message
            history_text = MessageView.format_download_history(downloads)
            await message.reply(history_text)
            
        except Exception as e:
            await message.reply("Error retrieving download history.")
            raise

    @router.message(Command("help"))
    async def help_command(message: Message, state: FSMContext):
        """Handle /help command"""
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

        await message.reply(help_text, parse_mode="Markdown")

    @router.message(Command("about"))
    async def about_command(message: Message, state: FSMContext):
        """Handle /about command"""
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

        await message.reply(about_text, parse_mode="Markdown")

    # Register all routes
    dp.include_router(router)
