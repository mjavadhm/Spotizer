from bale_bot.controllers.user_controller import BaleUserController
from bale_bot.controllers.download_controller import BaleDownloadController
from bale_bot.controllers.playlist_controller import BalePlaylistController
from bale_bot.views.message_view import MessageView
from bale_bot.views.music_view import MusicView
from bale_bot.views.playlist_view import PlaylistView
from bale_bot.bot import bot
from logger import get_logger

logger = get_logger(__name__)


def setup_callback_routes(user_controller: BaleUserController, download_controller: BaleDownloadController, playlist_controller: BalePlaylistController):
    """Set up callback query handlers for Bale bot"""
    logger.info("Setting up callback routes for Bale")

    @bot.on_callback_query(filters=lambda c: c.data.startswith("playlist:"))
    async def playlist_callback(callback_query):
        """Handle playlist-related callbacks"""
        try:
            parts = callback_query.data.split(":")
            action = parts[1]
            user_id = callback_query.from_user.id
            logger.info(f"Processing playlist callback for user {user_id} - Action: {action}")

            if action == "add":
                await playlist_controller.add_action(user_id, callback_query)
            
            elif action == "view_tracks":
                playlist_id = int(parts[2])
                page = int(parts[3]) if len(parts) > 3 else 1
                
                success, tracks = await playlist_controller.get_playlist_tracks(user_id, playlist_id)
                if success and tracks:
                    success_pl, playlists = await playlist_controller.get_user_playlists(user_id)
                    playlist = next((p for p in playlists if p.playlist_id == playlist_id), None)
                    
                    if playlist:
                        text = PlaylistView.format_playlist_tracks(playlist.name, tracks, page)
                        keyboard = PlaylistView.get_playlist_track_keyboard(tracks, playlist_id, page)
                        await callback_query.message.edit_text(text, reply_markup=keyboard)
                else:
                    await callback_query.answer("No tracks in this playlist")
                await callback_query.answer()
            
            elif action == "download_all":
                playlist_id = int(parts[2])
                success, tracks = await playlist_controller.get_playlist_tracks(user_id, playlist_id)
                
                if success and tracks:
                    keyboard = PlaylistView.get_download_all_keyboard(playlist_id, len(tracks))
                    await callback_query.message.edit_reply_markup(reply_markup=keyboard)
                    await callback_query.answer(f"Download {len(tracks)} tracks?")
                else:
                    await callback_query.answer("No tracks to download")
            
            elif action == "confirm_download":
                playlist_id = int(parts[2])
                await callback_query.answer("Starting download...")
                
                success, tracks = await playlist_controller.get_playlist_tracks(user_id, playlist_id)
                if success and tracks:
                    await callback_query.message.answer(f"⏳ Downloading {len(tracks)} tracks from playlist...")
                    
                    # Download each track
                    for idx, track in enumerate(tracks, 1):
                        try:
                            track_url = f"https://www.deezer.com/track/{track['id']}"
                            await download_controller.process_download_request(user_id, track_url)
                        except Exception as e:
                            logger.error(f"Error downloading track {track['id']}: {str(e)}")
                    
                    await callback_query.message.answer(f"✅ Downloaded {len(tracks)} tracks!")
            
            elif action == "delete":
                playlist_id = int(parts[2])
                success, msg = await playlist_controller.delete_playlist(user_id, playlist_id)
                
                if success:
                    await callback_query.message.edit_text(f"✅ {msg}")
                    await callback_query.answer("Playlist deleted")
                else:
                    await callback_query.answer(msg, show_alert=True)
            
            elif action == "remove_track":
                playlist_id = int(parts[2])
                playlist_track_id = int(parts[3])
                
                success, msg = await playlist_controller.remove_from_playlist(user_id, playlist_id, playlist_track_id)
                await callback_query.answer(msg)
                
                if success:
                    # Refresh the track list
                    success, tracks = await playlist_controller.get_playlist_tracks(user_id, playlist_id)
                    success_pl, playlists = await playlist_controller.get_user_playlists(user_id)
                    playlist = next((p for p in playlists if p.playlist_id == playlist_id), None)
                    
                    if playlist and tracks:
                        text = PlaylistView.format_playlist_tracks(playlist.name, tracks, 1)
                        keyboard = PlaylistView.get_playlist_track_keyboard(tracks, playlist_id, 1)
                        await callback_query.message.edit_text(text, reply_markup=keyboard)
                    else:
                        await callback_query.message.edit_text(f"🎶 *{playlist.name}*\n\nNo tracks in this playlist.")
            
            elif action == "page":
                playlist_id = int(parts[2])
                page = int(parts[3])
                
                success, tracks = await playlist_controller.get_playlist_tracks(user_id, playlist_id)
                success_pl, playlists = await playlist_controller.get_user_playlists(user_id)
                playlist = next((p for p in playlists if p.playlist_id == playlist_id), None)
                
                if playlist and tracks:
                    text = PlaylistView.format_playlist_tracks(playlist.name, tracks, page)
                    keyboard = PlaylistView.get_playlist_track_keyboard(tracks, playlist_id, page)
                    await callback_query.message.edit_text(text, reply_markup=keyboard)
                await callback_query.answer()
            
            elif action == "back_to_list":
                success, playlists = await playlist_controller.get_user_playlists(user_id)
                if success and playlists:
                    keyboard = PlaylistView.get_playlist_keyboard(playlists)
                    await callback_query.message.edit_text(
                        PlaylistView.get_choose_playlist_message(),
                        reply_markup=keyboard
                    )
                else:
                    await callback_query.message.edit_text("You have no playlists.")
                await callback_query.answer()
                
        except Exception as e:
            logger.error(f"Error in playlist callback: {str(e)}", exc_info=True)
            await callback_query.answer("Error processing request", show_alert=True)

    @bot.on_callback_query(filters=lambda c: c.data.startswith("select_playlist:"))
    async def select_playlist_callback(callback_query):
        """Handle playlist selection from /playlists command"""
        try:
            user_id = callback_query.from_user.id
            playlist_id = int(callback_query.data.split(":")[1])
            logger.info(f"User {user_id} selected playlist {playlist_id}")
            
            # Get playlist info
            success, playlists = await playlist_controller.get_user_playlists(user_id)
            playlist = next((p for p in playlists if p.playlist_id == playlist_id), None)
            
            if playlist:
                # Check if playlist has tracks
                success_tracks, tracks = await playlist_controller.get_playlist_tracks(user_id, playlist_id)
                has_tracks = success_tracks and len(tracks) > 0
                
                keyboard = PlaylistView.get_playlist_details_keyboard(playlist_id, has_tracks)
                text = f"🎶 *{playlist.name}*\n\n"
                if playlist.description:
                    text += f"_{playlist.description}_\n\n"
                text += f"Tracks: {len(tracks) if has_tracks else 0}"
                
                await callback_query.message.edit_text(
                    text,
                    reply_markup=keyboard
                )
            else:
                await callback_query.answer("Playlist not found", show_alert=True)
            
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"Error selecting playlist: {str(e)}", exc_info=True)
            await callback_query.answer("Error loading playlist", show_alert=True)

    @bot.on_callback_query(filters=lambda c: c.data.startswith("setting:"))
    async def settings_callback(callback_query):
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
            logger.error(f"Settings callback error: {str(e)}", exc_info=True)
            await callback_query.answer("Error processing settings")

    @bot.on_callback_query(filters=lambda c: c.data.startswith("set_quality:"))
    async def set_quality_callback(callback_query):
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
            logger.error(f"Quality setting error: {str(e)}", exc_info=True)
            await callback_query.answer("Error updating quality")

    @bot.on_callback_query(filters=lambda c: c.data.startswith("search:"))
    async def search_callback(callback_query):
        """Handle search-related callbacks"""
        try:
            # Extract search type and query
            _, search_type, query = callback_query.data.split(":", 2)
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
                reply_markup=keyboard
            )
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"Search callback error: {str(e)}", exc_info=True)
            await callback_query.answer("Error processing search")

    @bot.on_callback_query(filters=lambda c: c.data.startswith("page:"))
    async def page_callback(callback_query):
        """Handle pagination callbacks"""
        try:
            # Extract page info
            parts = callback_query.data.split(":")
            page = int(parts[1])
            search_type = parts[2]
            query = parts[3]
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
                reply_markup=keyboard
            )
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"Page callback error: {str(e)}", exc_info=True)
            await callback_query.answer("Error loading page")

    @bot.on_callback_query(filters=lambda c: c.data.startswith("select:"))
    async def select_callback(callback_query):
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

            # For Bale, send as new message with photo if available
            if item_info.get('image'):
                await callback_query.message.reply_photo(
                    photo=item_info['image'],
                    caption=text,
                    reply_markup=keyboard
                )
            else:
                await callback_query.message.reply(
                    text,
                    reply_markup=keyboard
                )
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"Selection callback error: {str(e)}", exc_info=True)
            await callback_query.answer("Error processing selection")

    @bot.on_callback_query(filters=lambda c: c.data.startswith("view:"))
    async def view_callback(callback_query):
        """Handle view callbacks (e.g., viewing album/playlist tracks)"""
        try:
            # Extract view info
            parts = callback_query.data.split(":")
            content_type = parts[1]
            action = parts[2]
            item_id = parts[3]
            page = int(parts[4])
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
                text = f"Tracks in album '{item_info['name']}':"
                keyboard = MusicView.get_list_keyboard(tracks, content_type, action, page, item_id)
            elif content_type == "playlist":
                tracks = item_info.get('tracks', [])
                text = f"Tracks in playlist '{item_info['name']}':"
                keyboard = MusicView.get_list_keyboard(tracks, content_type, action, page, item_id)
            elif content_type == "artist":
                from services.deezer_service import DeezerAPIClient
                if action == "top_tracks":
                    tracks = await DeezerAPIClient.get_artist_top_tracks(item_id)
                    text = f"Top tracks by {item_info['name']}:"
                    keyboard = MusicView.get_list_keyboard(tracks, content_type, action, page, item_id)
                elif action == "album":
                    albums = await DeezerAPIClient.get_artist_albums(item_id)
                    text = f"Albums by {item_info['name']}:\n\n"
                    keyboard = MusicView.get_list_keyboard(albums, content_type, action, page, item_id)
                elif action == "related":
                    related_artists = await DeezerAPIClient.get_artist_related(item_id)
                    text = f"Artists related to {item_info['name']}:\n\n"
                    keyboard = MusicView.get_list_keyboard(related_artists, content_type, action, page, item_id)
            
            await callback_query.message.edit_caption(
                caption=text,
                reply_markup=keyboard
            )
            await callback_query.answer()
            
        except Exception as e:
            logger.error(f"View callback error: {str(e)}", exc_info=True)
            await callback_query.answer("Error displaying tracks")

    @bot.on_callback_query(filters=lambda c: c.data.startswith("download:"))
    async def download_callback(callback_query):
        """Handle download callbacks"""
        try:
            # Extract download info
            _, content_type, item_id = callback_query.data.split(":")
            user_id = callback_query.from_user.id
            logger.info(f"Processing download for user {user_id} - Type: {content_type}, ID: {item_id}")
            
            # Answer callback query IMMEDIATELY to remove loading state
            await callback_query.answer()
            
            # Send processing message
            status_message = await callback_query.message.reply("⏳")
            
            if content_type == "artist":
                from services.deezer_service import DeezerAPIClient
                albums = await DeezerAPIClient.get_artist_albums(item_id)
                if not albums:
                    success, result = False, "No albums found for this artist."
                else:
                    total_tracks = sum(album.get('nb_tracks', 0) for album in albums)
                    
                    # Ask for confirmation
                    from balethon.objects import InlineKeyboardMarkup, InlineKeyboardButton
                    confirm_kb = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton(text="✅ Yes, Download All", callback_data=f"confirm_dl:artist:{item_id}"),
                            InlineKeyboardButton(text="❌ Cancel", callback_data="delete")
                        ]
                    ])
                    await bot.send_message(
                        user_id,
                        f"📥 Found {len(albums)} albums/EPs ({total_tracks} total tracks) for this artist.\n\nDo you want to download the entire discography?",
                        reply_markup=confirm_kb
                    )
                    
                    if status_message:
                        try:
                            await status_message.delete()
                        except:
                            pass
                    return
            else:
                target_url = f"https://www.deezer.com/{content_type}/{item_id}"
                logger.info(f"Using Deezer URL for download: {target_url}")

                success, result = await download_controller.process_download_request(
                    user_id=user_id,
                    url=target_url
                )
            
            # Clean up status message
            if status_message:
                try:
                    await status_message.delete()
                except:
                    pass
            
            if not success:
                logger.error(f"Download failed/partial for user {user_id}: {result}")
                return
            
            logger.info(f"Download completed successfully for user {user_id}")
            
        except Exception as e:
            logger.error(f"Download callback error: {str(e)}", exc_info=True)
            try:
                await callback_query.answer("Error processing download", show_alert=True)
            except:
                pass

    @bot.on_callback_query(filters=lambda c: c.data.startswith("confirm_dl:"))
    async def confirm_dl_callback(callback_query):
        """Handle confirmed download callbacks"""
        try:
            _, content_type, item_id = callback_query.data.split(":")
            user_id = callback_query.from_user.id
            
            await callback_query.message.edit_text("⏳ Request added to download queue...")
            await callback_query.answer()
            
            if content_type == "artist":
                from services.deezer_service import DeezerAPIClient
                albums = await DeezerAPIClient.get_artist_albums(item_id)
                if not albums:
                    await bot.send_message(user_id, "❌ No albums found for this artist.")
                    return
                
                await bot.send_message(user_id, f"📥 Starting download of {len(albums)} albums...")
                for album in albums:
                    album_url = f"https://www.deezer.com/album/{album['id']}"
                    logger.info(f"Downloading artist album: {album['name']} - {album_url}")
                    try:
                        s, r = await download_controller.process_download_request(user_id=user_id, url=album_url)
                        if not s:
                            await bot.send_message(user_id, f"❌ Failed to download {album['name']}: {r}")
                    except Exception as e:
                        logger.error(f"Error downloading album {album['name']}: {e}")
                
                await bot.send_message(user_id, "✅ Finished processing discography.")
                
        except Exception as e:
            logger.error(f"Confirm download callback error: {str(e)}", exc_info=True)
            await callback_query.answer("Error processing request")

    @bot.on_callback_query(filters=lambda c: c.data == "delete")
    async def delete_callback(callback_query):
        """Handle message deletion callbacks"""
        try:
            user_id = callback_query.from_user.id
            logger.info(f"Processing delete request from user {user_id}")
            await callback_query.message.delete()
            await callback_query.answer()
            logger.info(f"Message deleted for user {user_id}")
        except Exception as e:
            logger.error(f"Delete callback error: {str(e)}", exc_info=True)
            await callback_query.answer("Error deleting message")

    @bot.on_callback_query(filters=lambda c: c.data.startswith("rate:"))
    async def rate_callback(callback_query):
        """Handle like/dislike rating callbacks"""
        try:
            # Parse: rate:like:123 or rate:dislike:123
            parts = callback_query.data.split(":")
            action = parts[1]
            download_id = int(parts[2])
            user_id = callback_query.from_user.id
            
            rating = 1 if action == "like" else -1
            logger.info(f"User {user_id} rating download {download_id} as {action}")
            
            success, msg = await download_controller.update_download_rating(user_id, download_id, rating)
            
            if success:
                emoji = "👍" if rating == 1 else "👎"
                await callback_query.answer(f"{emoji} {'Liked' if rating == 1 else 'Disliked'}!")
                # Update keyboard to show which button was clicked
                try:
                    new_keyboard = MusicView.get_rating_keyboard(download_id, rating)
                    await callback_query.message.edit_reply_markup(reply_markup=new_keyboard)
                except:
                    pass
            else:
                await callback_query.answer(msg, show_alert=True)
                
        except Exception as e:
            logger.error(f"Rate callback error: {str(e)}", exc_info=True)
            await callback_query.answer("Error updating rating")

    logger.info("Callback routes setup completed for Bale")
