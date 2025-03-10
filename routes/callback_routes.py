import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from controllers.user_controller import UserController
from controllers.download_controller import DownloadController
from views.message_view import MessageView
from views.music_view import MusicView

logger = logging.getLogger(__name__)

def setup_callback_routes(dp: Router, user_controller: UserController, download_controller: DownloadController):
    """Set up callback query handlers"""
    router = Router()

    @router.callback_query(F.data.startswith("setting:"))
    async def settings_callback(callback_query: CallbackQuery, state: FSMContext):
        """Handle settings-related callbacks"""
        try:
            action = callback_query.data.split(":")[1]
            user_id = callback_query.from_user.id
            
            if action == "change_quality":
                # Show quality options
                success, settings = await user_controller.get_user_settings(user_id)
                if not success:
                    await callback_query.answer("Error accessing settings")
                    return
                
                keyboard = MessageView.get_quality_options_keyboard(settings['download_quality'])
                await callback_query.message.edit_reply_markup(reply_markup=keyboard)
                await callback_query.answer()
                
            elif action == "toggle_zip":
                # Toggle ZIP setting
                success, settings = await user_controller.get_user_settings(user_id)
                if not success:
                    await callback_query.answer("Error accessing settings")
                    return
                
                new_zip_setting = not settings['make_zip']
                success, _ = await user_controller.update_user_settings(
                    user_id,
                    {'make_zip': new_zip_setting}
                )
                
                if success:
                    # Update keyboard
                    settings['make_zip'] = new_zip_setting
                    keyboard = MessageView.get_settings_keyboard(settings)
                    await callback_query.message.edit_reply_markup(reply_markup=keyboard)
                    await callback_query.answer(f"ZIP mode {'enabled' if new_zip_setting else 'disabled'}")
                else:
                    await callback_query.answer("Error updating settings")
                    
        except Exception as e:
            logger.error(f"Settings callback error: {str(e)}")
            await callback_query.answer("Error processing settings")
            raise

    @router.callback_query(F.data.startswith("set_quality:"))
    async def set_quality_callback(callback_query: CallbackQuery, state: FSMContext):
        """Handle quality setting callbacks"""
        try:
            quality = callback_query.data.split(":")[1]
            user_id = callback_query.from_user.id
            
            if quality == "back":
                # Return to main settings
                success, settings = await user_controller.get_user_settings(user_id)
                if success:
                    keyboard = MessageView.get_settings_keyboard(settings)
                    await callback_query.message.edit_reply_markup(reply_markup=keyboard)
                    await callback_query.answer("Back to settings")
                return
            
            # Update quality setting
            success, _ = await user_controller.update_user_settings(
                user_id,
                {'download_quality': quality}
            )
            
            if success:
                await callback_query.answer(f"Quality set to {quality}")
                # Update keyboard
                success, settings = await user_controller.get_user_settings(user_id)
                if success:
                    keyboard = MessageView.get_quality_options_keyboard(quality)
                    await callback_query.message.edit_reply_markup(reply_markup=keyboard)
            else:
                await callback_query.answer("Error updating quality setting")
                
        except Exception as e:
            logger.error(f"Quality setting error: {str(e)}")
            await callback_query.answer("Error updating quality")
            raise

    @router.callback_query(F.data.startswith("search:"))
    async def search_callback(callback_query: CallbackQuery, state: FSMContext):
        """Handle search-related callbacks"""
        try:
            # Extract search type and query
            _, search_type, query = callback_query.data.split(":")
            
            # Perform search
            success, results = await download_controller.search(query, search_type, page=1)
            if not success:
                await callback_query.answer("Search failed")
                return
            
            # Display results
            text, keyboard = MusicView.format_search_results(results, search_type, query, page=1)
            await callback_query.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"Search callback error: {str(e)}")
            await callback_query.answer("Error processing search")
            raise

    @router.callback_query(F.data.startswith("select:"))
    async def select_callback(callback_query: CallbackQuery, state: FSMContext):
        """Handle item selection callbacks"""
        try:
            # Extract selection info
            _, content_type, item_id = callback_query.data.split(":")
            
            # Get item details
            success, item_info = await download_controller.get_item_info(content_type, item_id)
            if not success:
                await callback_query.answer("Error getting item information")
                return
            
            # Format and display item information
            if content_type == "track":
                text = MusicView.format_track_info(item_info)
                keyboard = MusicView.get_track_keyboard(item_info)
            elif content_type == "album":
                text = MusicView.format_album_info(item_info)
                keyboard = MusicView.get_album_keyboard(item_info)
            elif content_type == "playlist":
                text = MusicView.format_playlist_info(item_info)
                keyboard = MusicView.get_playlist_keyboard(item_info)
            else:
                await callback_query.answer("Invalid content type")
                return
            
            await callback_query.message.edit_caption(
                caption=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"Selection callback error: {str(e)}")
            await callback_query.answer("Error processing selection")
            raise

    @router.callback_query(F.data.startswith("download:"))
    async def download_callback(callback_query: CallbackQuery, state: FSMContext):
        """Handle download callbacks"""
        try:
            # Extract download info
            _, content_type, item_id = callback_query.data.split(":")
            
            # Send processing message
            status_message = await callback_query.message.reply("⏳ Processing download...")
            
            # Process download
            success, result = await download_controller.process_item_download(
                user_id=callback_query.from_user.id,
                content_type=content_type,
                item_id=item_id
            )
            
            # Clean up status message
            await status_message.delete()
            
            if not success:
                await callback_query.answer("Download failed")
                return
            
            await callback_query.answer("Download complete")
            
        except Exception as e:
            logger.error(f"Download callback error: {str(e)}")
            await callback_query.answer("Error processing download")
            if 'status_message' in locals():
                await status_message.delete()
            raise

    @router.callback_query(F.data == "delete")
    async def delete_callback(callback_query: CallbackQuery):
        """Handle message deletion callbacks"""
        try:
            await callback_query.message.delete()
            await callback_query.answer()
        except Exception as e:
            logger.error(f"Delete callback error: {str(e)}")
            await callback_query.answer("Error deleting message")

    # Register all routes
    dp.include_router(router)
