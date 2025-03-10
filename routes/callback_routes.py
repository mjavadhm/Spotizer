from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from controllers.user_controller import UserController
from controllers.download_controller import DownloadController
from views.message_view import MessageView
from views.music_view import MusicView
from logger import get_logger

logger = get_logger(__name__)

def setup_callback_routes(dp: Router, user_controller: UserController, download_controller: DownloadController):
    """Set up callback query handlers"""
    router = Router()
    logger.info("Setting up callback routes")

    @router.callback_query(F.data.startswith("setting:"))
    async def settings_callback(callback_query: CallbackQuery, state: FSMContext):
        """Handle settings-related callbacks"""
        try:
            action = callback_query.data.split(":")[1]
            user_id = callback_query.from_user.id
            logger.info(f"Processing settings callback for user {user_id} - Action: {action}")
            
            if action == "change_quality":
                logger.info(f"User {user_id} requested quality change")
                success, settings = await user_controller.get_user_settings(user_id)
                if not success:
                    logger.error(f"Failed to get settings for user {user_id}")
                    await callback_query.answer("Error accessing settings")
                    return
                
                keyboard = MessageView.get_quality_options_keyboard(settings['download_quality'])
                await callback_query.message.edit_reply_markup(reply_markup=keyboard)
                await callback_query.answer()
                logger.info(f"Displayed quality options for user {user_id}")
                
            elif action == "toggle_zip":
                logger.info(f"User {user_id} requested ZIP toggle")
                success, settings = await user_controller.get_user_settings(user_id)
                if not success:
                    logger.error(f"Failed to get settings for user {user_id}")
                    await callback_query.answer("Error accessing settings")
                    return
                
                new_zip_setting = not settings['make_zip']
                success, _ = await user_controller.update_user_settings(
                    user_id,
                    {'make_zip': new_zip_setting}
                )
                
                if success:
                    settings['make_zip'] = new_zip_setting
                    keyboard = MessageView.get_settings_keyboard(settings)
                    await callback_query.message.edit_reply_markup(reply_markup=keyboard)
                    await callback_query.answer(f"ZIP mode {'enabled' if new_zip_setting else 'disabled'}")
                    logger.info(f"Updated ZIP setting for user {user_id} to {new_zip_setting}")
                else:
                    logger.error(f"Failed to update ZIP setting for user {user_id}")
                    await callback_query.answer("Error updating settings")
                    
        except Exception as e:
            logger.error(f"Settings callback error for user {user_id}: {str(e)}", exc_info=True)
            await callback_query.answer("Error processing settings")
            raise

    @router.callback_query(F.data.startswith("set_quality:"))
    async def set_quality_callback(callback_query: CallbackQuery, state: FSMContext):
        """Handle quality setting callbacks"""
        try:
            quality = callback_query.data.split(":")[1]
            user_id = callback_query.from_user.id
            logger.info(f"Processing quality setting for user {user_id} - Quality: {quality}")
            
            if quality == "back":
                logger.info(f"User {user_id} requested return to main settings")
                success, settings = await user_controller.get_user_settings(user_id)
                if success:
                    keyboard = MessageView.get_settings_keyboard(settings)
                    await callback_query.message.edit_reply_markup(reply_markup=keyboard)
                    await callback_query.answer("Back to settings")
                    logger.info(f"Returned to main settings for user {user_id}")
                return
            
            # Update quality setting
            success, _ = await user_controller.update_user_settings(
                user_id,
                {'download_quality': quality}
            )
            
            if success:
                logger.info(f"Updated quality setting for user {user_id} to {quality}")
                await callback_query.answer(f"Quality set to {quality}")
                success, settings = await user_controller.get_user_settings(user_id)
                if success:
                    keyboard = MessageView.get_quality_options_keyboard(quality)
                    await callback_query.message.edit_reply_markup(reply_markup=keyboard)
            else:
                logger.error(f"Failed to update quality setting for user {user_id}")
                await callback_query.answer("Error updating quality setting")
                
        except Exception as e:
            logger.error(f"Quality setting error for user {user_id}: {str(e)}", exc_info=True)
            await callback_query.answer("Error updating quality")
            raise

    @router.callback_query(F.data.startswith("search:"))
    async def search_callback(callback_query: CallbackQuery, state: FSMContext):
        """Handle search-related callbacks"""
        try:
            _, search_type, query = callback_query.data.split(":")
            user_id = callback_query.from_user.id
            logger.info(f"Processing search callback for user {user_id} - Type: {search_type}, Query: {query}")
            
            success, results = await download_controller.search(query, search_type, page=1)
            if not success:
                logger.error(f"Search failed for user {user_id} - Query: {query}")
                await callback_query.answer("Search failed")
                return
            
            logger.info(f"Found {len(results)} results for user {user_id}")
            text, keyboard = MusicView.format_search_results(results, search_type, query, page=1)
            await callback_query.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"Search callback error for user {user_id}: {str(e)}", exc_info=True)
            await callback_query.answer("Error processing search")
            raise

    @router.callback_query(F.data.startswith("select:"))
    async def select_callback(callback_query: CallbackQuery, state: FSMContext):
        """Handle item selection callbacks"""
        try:
            _, content_type, item_id = callback_query.data.split(":")
            user_id = callback_query.from_user.id
            logger.info(f"Processing selection for user {user_id} - Type: {content_type}, ID: {item_id}")
            
            success, item_info = await download_controller.get_item_info(content_type, item_id)
            if not success:
                logger.error(f"Failed to get item info for user {user_id} - ID: {item_id}")
                await callback_query.answer("Error getting item information")
                return
            
            logger.info(f"Retrieved item info for user {user_id}")
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
                logger.error(f"Invalid content type for user {user_id}: {content_type}")
                await callback_query.answer("Invalid content type")
                return
            
            await callback_query.message.edit_caption(
                caption=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback_query.answer()
            logger.info(f"Displayed item info for user {user_id}")
            
        except Exception as e:
            logger.error(f"Selection callback error for user {user_id}: {str(e)}", exc_info=True)
            await callback_query.answer("Error processing selection")
            raise

    @router.callback_query(F.data.startswith("download:"))
    async def download_callback(callback_query: CallbackQuery, state: FSMContext):
        """Handle download callbacks"""
        try:
            _, content_type, item_id = callback_query.data.split(":")
            user_id = callback_query.from_user.id
            logger.info(f"Processing download for user {user_id} - Type: {content_type}, ID: {item_id}")
            
            status_message = await callback_query.message.reply("⏳ Processing download...")
            logger.info(f"Sent processing message for user {user_id}")
            
            success, result = await download_controller.process_item_download(
                user_id=user_id,
                content_type=content_type,
                item_id=item_id
            )
            
            await status_message.delete()
            
            if not success:
                logger.error(f"Download failed for user {user_id} - Result: {result}")
                await callback_query.answer("Download failed")
                return
            
            logger.info(f"Download completed for user {user_id}")
            await callback_query.answer("Download complete")
            
        except Exception as e:
            logger.error(f"Download callback error for user {user_id}: {str(e)}", exc_info=True)
            await callback_query.answer("Error processing download")
            if 'status_message' in locals():
                await status_message.delete()
            raise

    @router.callback_query(F.data == "delete")
    async def delete_callback(callback_query: CallbackQuery):
        """Handle message deletion callbacks"""
        try:
            user_id = callback_query.from_user.id
            logger.info(f"Processing delete request from user {user_id}")
            await callback_query.message.delete()
            await callback_query.answer()
            logger.info(f"Message deleted for user {user_id}")
        except Exception as e:
            logger.error(f"Delete callback error for user {user_id}: {str(e)}", exc_info=True)
            await callback_query.answer("Error deleting message")

    # Register all routes
    dp.include_router(router)
    logger.info("Callback routes setup completed")
