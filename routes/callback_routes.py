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
                success, settings = await user_controller.get_user_settings(user_id)
                if not success:
                    logger.error(f"Failed to get settings for user {user_id}")
                    await callback_query.answer("Error accessing settings")
                    return
                
                keyboard = MessageView.get_quality_options_keyboard(settings['download_quality'])
                await callback_query.message.edit_reply_markup(reply_markup=keyboard)
                await callback_query.answer()
                
            elif action == "toggle_zip":
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
                success, settings = await user_controller.get_user_settings(user_id)
                if success:
                    keyboard = MessageView.get_settings_keyboard(settings)
                    await callback_query.message.edit_reply_markup(reply_markup=keyboard)
                    await callback_query.answer("Back to settings")
                return
            
            success, _ = await user_controller.update_user_settings(
                user_id,
                {'download_quality': quality}
            )
            
            if success:
                await callback_query.answer(f"Quality set to {quality}")
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
            # Extract search type and query
            _, search_type, query = callback_query.data.split(":")
            user_id = callback_query.from_user.id
            logger.info(f"Processing search for user {user_id} - Type: {search_type}, Query: {query}")
            
            # Perform search
            success, results = await download_controller.search(query, search_type, page=1)
            if not success:
                logger.error(f"Search failed for user {user_id}")
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
            logger.error(f"Search callback error for user {user_id}: {str(e)}", exc_info=True)
            await callback_query.answer("Error processing search")
            raise

    @router.callback_query(F.data.startswith("page:"))
    async def page_callback(callback_query: CallbackQuery, state: FSMContext):
        """Handle pagination callbacks"""
        try:
            # Extract page info
            _, page, search_type, query = callback_query.data.split(":")
            page = int(page)
            user_id = callback_query.from_user.id
            logger.info(f"Processing page {page} for user {user_id}")
            
            # Perform search with pagination
            success, results = await download_controller.search(query, search_type, page=page)
            if not success:
                logger.error(f"Page search failed for user {user_id}")
                await callback_query.answer("Failed to load more results")
                return
            
            # Display results
            text, keyboard = MusicView.format_search_results(results, search_type, query, page=page)
            await callback_query.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"Page callback error for user {user_id}: {str(e)}", exc_info=True)
            await callback_query.answer("Error loading page")
            raise

    @router.callback_query(F.data.startswith("select:"))
    async def select_callback(callback_query: CallbackQuery, state: FSMContext):
        """Handle item selection callbacks"""
        try:
            # Extract selection info
            _, content_type, item_id = callback_query.data.split(":")
            user_id = callback_query.from_user.id
            logger.info(f"Processing selection for user {user_id} - Type: {content_type}, ID: {item_id}")
            
            # Get item details
            success, item_info = await download_controller.get_item_info(content_type, item_id)
            if not success:
                logger.error(f"Failed to get item info for user {user_id}")
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
            elif content_type == "artist":
                text = MusicView.format_artist_info(item_info)
                keyboard = MusicView.get_artist_keyboard(item_info)
            else:
                logger.error(f"Invalid content type for user {user_id}: {content_type}")
                await callback_query.answer("Invalid content type")
                return

            await callback_query.message.answer_photo(
                photo=item_info['image'],
                caption=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"Selection callback error for user {user_id}: {str(e)}", exc_info=True)
            await callback_query.answer("Error processing selection")
            raise

    @router.callback_query(F.data.startswith("view:"))
    async def view_callback(callback_query: CallbackQuery, state: FSMContext):
        """Handle view callbacks (e.g., viewing album/playlist tracks)"""
        try:
            # Extract view info
            _, content_type, action, item_id = callback_query.data.split(":")
            user_id = callback_query.from_user.id
            logger.info(f"Processing view for user {user_id} - Type: {content_type}, Action: {action}")
            
            # Get item details
            success, item_info = await download_controller.get_item_info(content_type, item_id)
            if not success:
                logger.error(f"Failed to get item info for user {user_id}")
                await callback_query.answer("Error getting item information")
                return
            
            # Display tracks based on content type
            if content_type == "album":
                tracks = item_info.get('tracks', [])
                text = f"Tracks in album '{item_info['name']}':\n\n"
                for track in tracks:
                    text += f"{track['track_number']}. {track['name']} ({track['duration']})\n"
            elif content_type == "playlist":
                tracks = item_info.get('tracks', [])
                text = f"Tracks in playlist '{item_info['name']}':\n\n"
                for i, track in enumerate(tracks, 1):
                    text += f"{i}. {track['name']} - {track['main_artist']} ({track['duration']})\n"
            elif content_type == "artist":
                if action == "top_tracks":
                    tracks = await download_controller.get_artist_top_tracks(item_id)
                    text = f"Top tracks by {item_info['name']}:\n\n"
                    for i, track in enumerate(tracks, 1):
                        text += f"{i}. {track['name']} ({track['duration']})\n"
                elif action == "albums":
                    albums = await download_controller.get_artist_albums(item_id)
                    text = f"Albums by {item_info['name']}:\n\n"
                    for i, album in enumerate(albums, 1):
                        text += f"{i}. {album['name']} ({album['release_date']})\n"
                elif action == "related":
                    artists = await download_controller.get_related_artists(item_id)
                    text = f"Artists related to {item_info['name']}:\n\n"
                    for i, artist in enumerate(artists, 1):
                        text += f"{i}. {artist['name']}\n"
            
            # Add back button
            keyboard = MusicView.get_back_keyboard(content_type, item_id)
            
            await callback_query.message.answer_photo(
                photo=item_info['image'],
                caption=text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"View callback error for user {user_id}: {str(e)}", exc_info=True)
            await callback_query.answer("Error displaying tracks")
            raise

    @router.callback_query(F.data.startswith("download:"))
    async def download_callback(callback_query: CallbackQuery, state: FSMContext):
        """Handle download callbacks"""
        try:
            # Extract download info
            _, content_type, item_id = callback_query.data.split(":")
            user_id = callback_query.from_user.id
            logger.info(f"Processing download for user {user_id} - Type: {content_type}, ID: {item_id}")
            
            # Send processing message
            status_message = await callback_query.message.reply("⏳ Processing download...")
            
            # Convert Spotify URL to Deezer and process download
            spotify_url = f"https://open.spotify.com/{content_type}/{item_id}"
            success, result = await download_controller.process_download_request(
                user_id=user_id,
                url=spotify_url
            )
            
            # Clean up status message
            await status_message.delete()
            
            if not success:
                logger.error(f"Download failed for user {user_id}: {result}")
                await callback_query.answer("Download failed")
                return
            
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
            logger.error(f"Delete callback error for user {callback_query.from_user.id}: {str(e)}", exc_info=True)
            await callback_query.answer("Error deleting message")

    # Register all routes
    dp.include_router(router)
    logger.info("Callback routes setup completed")
