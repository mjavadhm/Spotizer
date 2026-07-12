import aiogram
import os
import shutil
from sqlalchemy.future import select
from sqlalchemy.sql import func
from database.session import async_session_maker
from controllers.user_controller import UserController
from models.base import User, UserSettings, UserDownload, Track
from services.deezer_service import DeezerService, DeezerAPIClient
from utils.file_handler import FileHandler
from utils.url_validator import URLValidator
from views.music_view import MusicView
from aiogram.types import FSInputFile
from bot import bot
from logger import get_logger

logger = get_logger(__name__)

class DownloadController:
    def __init__(self):
        self.deezer_service = DeezerService()
        self.file_handler = FileHandler()
        self.url_validator = URLValidator()
        logger.info("DownloadController initialized (Spotify support removed)")

    @staticmethod
    async def add_download(user_id, deezer_id, content_type, file_id, quality, url, title, artist, album, duration=None, file_name=None, channel_id=None, message_id=None):
        """Add a download to the database. Returns download_id for rating buttons.
        If the same track was already downloaded by this user, updates timestamp and returns existing download_id."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserDownload).where(
                    UserDownload.user_id == user_id,
                    UserDownload.deezer_id == deezer_id,
                    UserDownload.content_type == content_type,
                    UserDownload.quality == quality
                )
            )
            existing = result.scalars().first()
            
            if existing:
                existing.downloaded_at = func.now()
                existing.file_id = file_id
                await session.commit()
                return existing.download_id
            
            download = UserDownload(
                user_id=user_id,
                deezer_id=deezer_id,
                content_type=content_type,
                file_id=file_id,
                quality=quality,
                url=url,
                title=title,
                artist=artist,
                album=album,
                duration=duration,
                file_name=file_name,
            )
            session.add(download)
            await session.commit()
            await session.refresh(download)
            return download.download_id

    async def search(self, query: str, search_type: str, page: int = 1) -> tuple[bool, list]:
        """Search for music content using Deezer"""
        try:
            logger.info(f"Searching for {search_type}s with query: {query} (Page: {page})")
            
            offset = (page - 1) * 5
            results = await DeezerAPIClient.search(query, search_type, limit=5, offset=offset)
            
            if results:
                logger.info(f"Found {len(results)} {search_type}s for query: {query}")
                return True, results
            else:
                logger.warning(f"No {search_type}s found for query: {query}")
                return False, []
                
        except Exception as e:
            logger.error(f"Search error for {search_type}s - Query: {query}: {str(e)}", exc_info=True)
            return False, []

    async def get_item_info(self, content_type: str, item_id: str) -> tuple[bool, dict]:
        """Get detailed information about a music item"""
        try:
            logger.info(f"Getting info for {content_type} with ID: {item_id}")
            item_info = await DeezerAPIClient.get_item_info(content_type, item_id)
            
            if item_info:
                logger.info(f"Successfully retrieved info for {content_type} {item_id}")
                return True, item_info
            else:
                logger.warning(f"No info found for {content_type} {item_id}")
                return False, {}
                
        except Exception as e:
            logger.error(f"Error getting item info for {content_type} {item_id}: {str(e)}", exc_info=True)
            return False, {}

    async def get_artist_top_tracks(self, artist_id: str) -> list:
        """Get artist's top tracks"""
        try:
            logger.info(f"Getting top tracks for artist {artist_id}")
            return await DeezerAPIClient.get_artist_top_tracks(artist_id)
        except Exception as e:
            logger.error(f"Error getting artist top tracks: {str(e)}", exc_info=True)
            return []

    async def get_artist_albums(self, artist_id: str) -> list:
        """Get artist's albums"""
        try:
            logger.info(f"Getting albums for artist {artist_id}")
            return await DeezerAPIClient.get_artist_albums(artist_id)
        except Exception as e:
            logger.error(f"Error checking download limit: {str(e)}", exc_info=True)
            # Default to not limited if check fails to avoid blocking users
            return False, ""

    async def process_artist_discography(self, user_id: int, artist_id: str):
        """Asynchronously download and send an artist's discography in chunks of 5 albums."""
        try:
            from services.deezer_service import DeezerAPIClient
            albums = await DeezerAPIClient.get_artist_albums(artist_id)
            if not albums:
                await bot.send_message(chat_id=user_id, text="❌ No albums found for this artist.")
                return

            artist_name = albums[0].get('artist', 'Unknown Artist')

            # Get user settings
            async with async_session_maker() as session:
                settings = await session.execute(
                    select(UserSettings).where(UserSettings.user_id == user_id)
                )
                settings = settings.scalar_one_or_none()
                quality = settings.download_quality if settings else 'MP3_128'
                make_zip = settings.make_zip if settings else True

            chunk_size = 5
            total_chunks = (len(albums) + chunk_size - 1) // chunk_size
            total_steps = len(albums) + (total_chunks * 2 if make_zip else total_chunks)
            current_step = 0
            
            prog_msg = await bot.send_message(
                chat_id=user_id, 
                text=f"📥 *{artist_name} Discography*\n\n[□□□□□□□□□□] 0%\n⏳ Status: Preparing to download...",
                parse_mode="Markdown"
            )
            prog_msg_id = prog_msg.message_id
            
            async def update_prog(status_text):
                percent = int((current_step / total_steps) * 100) if total_steps > 0 else 0
                if percent > 100: percent = 100
                filled = percent // 10
                empty = 10 - filled
                bar = "■" * filled + "□" * empty
                text = f"📥 *{artist_name} Discography*\n\n[{bar}] {percent}%\n⏳ Status: {status_text}"
                try:
                    await bot.edit_message_text(chat_id=user_id, message_id=prog_msg_id, text=text, parse_mode="Markdown")
                except Exception:
                    pass
            
            for i in range(0, len(albums), chunk_size):
                chunk = albums[i:i + chunk_size]
                part_num = (i // chunk_size) + 1
                
                # Create a unique temporary directory for this chunk
                chunk_dir = os.path.join(self.deezer_service.download_dir, f"artist_{artist_id}_chunk_{part_num}")
                os.makedirs(chunk_dir, exist_ok=True)
                
                all_success = True
                for idx, album in enumerate(chunk):
                    await update_prog(f"Downloading album {idx+1}/{len(chunk)} (Part {part_num}/{total_chunks})...")
                    album_url = f"https://www.deezer.com/album/{album['id']}"
                    res = await self.deezer_service.download(album_url, quality_download=quality)
                    if res.success and res.tracks:
                        album_folder = os.path.dirname(res.tracks[0].file_path)
                        try:
                            album_name_folder = os.path.basename(album_folder)
                            target_path = os.path.join(chunk_dir, album_name_folder)
                            if os.path.exists(target_path):
                                target_path += f"_{album['id']}"
                            shutil.move(album_folder, target_path)
                            parent_dir = os.path.dirname(album_folder)
                            if not os.listdir(parent_dir):
                                os.rmdir(parent_dir)
                        except Exception as e:
                            logger.error(f"Failed to move {album_folder} to {chunk_dir}: {e}")
                            all_success = False
                    else:
                        all_success = False
                    
                    current_step += 1

                if not make_zip:
                    await update_prog(f"Sending audio files for Part {part_num}/{total_chunks}...")
                    musics_playlist = []
                    for root, _, files in os.walk(chunk_dir):
                        for file in files:
                            if file.lower().endswith(('.mp3', '.flac', '.m4a')):
                                file_path = os.path.join(root, file)
                                document = FSInputFile(file_path)
                                try:
                                    await bot.send_document(chat_id=user_id, document=document, caption=f"@Spotizer_bot 🎧")
                                    musics_playlist.append((file_path, 0, file))
                                except Exception as e:
                                    logger.error(f"Failed to send track: {e}")
                                    
                    playlist_name = f"{artist_name}_Discography_Part_{part_num}"
                    playlist_success, playlist_path = self.file_handler.create_m3u_playlist(musics_playlist, playlist_name)
                    if playlist_success:
                        await bot.send_document(chat_id=user_id, document=FSInputFile(playlist_path))
                        os.remove(playlist_path)
                    
                else:
                    title = f"{artist_name}_Discography_Part_{part_num}_of_{total_chunks}"
                    
                    await update_prog(f"Zipping Part {part_num}/{total_chunks}...")
                    import asyncio
                    zip_success, zip_path = await asyncio.to_thread(self.file_handler.zip_folder, chunk_dir, title)
                    current_step += 1
                    
                    if zip_success:
                        try:
                            await update_prog(f"Uploading Part {part_num}/{total_chunks}...")
                            document = FSInputFile(zip_path)
                            await bot.send_document(
                                chat_id=user_id,
                                document=document,
                                caption=f"@Spotizer_bot 🎧\n📀 {title}"
                            )
                        except Exception as e:
                            logger.error(f"Failed to send discography chunk {part_num} to user: {e}")
                            await bot.send_message(chat_id=user_id, text=f"❌ Failed to upload Part {part_num}.")
                        
                        if os.path.exists(zip_path):
                            os.remove(zip_path)
                            
                try:
                    shutil.rmtree(chunk_dir)
                except Exception as e:
                    logger.error(f"Failed to cleanup chunk directory {chunk_dir}: {e}")
                    
            try:
                await bot.delete_message(chat_id=user_id, message_id=prog_msg_id)
            except Exception:
                pass
            await bot.send_message(chat_id=user_id, text=f"✅ Discography download complete!")
        except Exception as e:
            logger.error(f"Error in process_artist_discography: {e}", exc_info=True)
            await bot.send_message(chat_id=user_id, text="❌ An error occurred while downloading the discography.")

    @staticmethod
    async def get_track(track_id):
        """Get a track from the database."""
        async with async_session_maker() as session:
            return await session.get(Track, track_id)

    @staticmethod
    async def add_track(track_id, url, file_id, title, artist, album, duration, quality, channel_id=None, message_id=None, spotify_id=None):
        """Add a track to the database."""
        async with async_session_maker() as session:
            async with session.begin():
                track = Track(
                    track_id=track_id,
                    spotify_id=spotify_id,
                    url=url,
                    file_id=file_id,
                    title=title,
                    artist=artist,
                    album=album,
                    duration=duration,
                    quality=quality,
                    channel_id=channel_id,
                    message_id=message_id,
                )
                session.add(track)
            await session.commit()

    @staticmethod
    async def get_track_by_deezer_id_quality(user_id, deezer_id, quality):
        """Get a track by deezer_id and quality."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserDownload)
                .where(
                    UserDownload.user_id == user_id,
                    UserDownload.deezer_id == deezer_id,
                    UserDownload.quality == quality,
                )
            )
            return result.scalars().first()

    async def process_download_request(self, user_id, url):
        """Process download request from user"""
        try:
            logger.info(f"Processing download request for user {user_id} - URL: {url}")
            
            if not self.url_validator.is_valid_url(url):
                logger.error(f"Invalid URL format provided by user {user_id}: {url}")
                return False, "Invalid URL format. Please provide a valid Deezer link."

            # Reject Spotify links directly
            if "spotify" in url.lower():
                logger.warning(f"User {user_id} tried to download a Spotify link: {url}")
                return False, "❌ Spotify links are no longer supported. Please use a Deezer link."

            success, user_settings = await UserController.get_user_settings(user_id)
            if not success:
                quality = 'MP3_320'
                make_zip = True
            else:
                quality = user_settings.get('download_quality', 'MP3_320')
                make_zip = user_settings.get('make_zip', True)
            
            logger.info(f"User {user_id} settings - Quality: {quality}, Make ZIP: {make_zip}")

            content_type, deezer_id = self.deezer_service.extract_info_from_url(url)
            if not content_type or not deezer_id:
                return False, "❌ Invalid URL format. Please provide a valid Deezer link."

            # Check for existing ZIP if album/playlist and make_zip is True
            if make_zip and content_type in ['album', 'playlist']:
                existing_zip = await self.get_track_by_deezer_id_quality(user_id, deezer_id, quality)
                if existing_zip:
                    logger.info(f"Found existing ZIP for {content_type} {deezer_id}")
                    await bot.send_document(
                        chat_id=user_id,
                        document=existing_zip.file_id,
                        caption=f"@Spotizer_bot 🎧"
                    )
                    return True, "Sent existing ZIP file"

            logger.info(f"Downloading {content_type}: {deezer_id}")
            result = await self.deezer_service.download(url, quality_download=quality)
            
            if not result.success:
                return False, f"❌ Download failed: {result.error}"

            # If it's an album or playlist, we can optionally zip it
            if result.is_album_or_playlist:
                if not result.tracks:
                    return False, "❌ Album/Playlist is empty or failed to download."
                
                # Assume all tracks are downloaded in one directory
                download_dir = os.path.dirname(result.tracks[0].file_path)
                
                # We need a title for the zip. Use the album title of the first track or a generic name.
                if content_type == 'album':
                    title = result.tracks[0].album if result.tracks[0].album else f"album_{deezer_id}"
                    artist = result.tracks[0].artist if result.tracks[0].artist else "Unknown Artist"
                    display_title = f"{title} - {artist}"
                elif content_type == 'artist':
                    title = f"artist_discography_{deezer_id}"
                    artist = result.tracks[0].artist if result.tracks[0].artist else "Unknown Artist"
                    display_title = f"{artist} - Full Discography"
                else:
                    title = f"playlist_{deezer_id}"
                    display_title = title
                    
                if make_zip:
                    if content_type == 'artist':
                        logger.info(f"Creating chunked ZIPs for {content_type} {deezer_id}")
                        import asyncio
                        zip_results = await asyncio.to_thread(self.file_handler.zip_directories_chunked, download_dir, title, chunk_size=5)
                        if not zip_results:
                            return False, "❌ Failed to create ZIP archive or no files found."
                        
                        music_channel_id = os.getenv('MUSIC_CHANNEL_ID')
                        
                        all_success = True
                        for zip_success, zip_path in zip_results:
                            if not zip_success:
                                all_success = False
                                continue
                            
                            document = FSInputFile(zip_path)
                            channel_msg_id = None
                            file_id_to_send = document
        
                            if music_channel_id:
                                try:
                                    channel_msg = await bot.send_document(
                                        chat_id=music_channel_id,
                                        document=document,
                                        caption=f"@Spotizer_bot 🎧\n📀 {display_title}"
                                    )
                                    channel_msg_id = channel_msg.message_id
                                    file_id_to_send = channel_msg.document.file_id
                                except Exception as e:
                                    logger.error(f"Failed to send to music channel: {e}")
        
                            try:
                                sent_message = await bot.send_document(
                                    chat_id=user_id, 
                                    document=file_id_to_send, 
                                    caption=f"@Spotizer_bot 🎧"
                                )
                                
                                await self.add_download(
                                    user_id=user_id,
                                    deezer_id=deezer_id,
                                    content_type=content_type,
                                    file_id=sent_message.document.file_id,
                                    quality=quality,
                                    url=url,
                                    title=title,
                                    artist="Unknown",
                                    album=None,
                                    channel_id=int(music_channel_id) if music_channel_id else None,
                                    message_id=channel_msg_id
                                )
                            except Exception as e:
                                logger.error(f"Failed to send chunked ZIP to user: {e}")
                                await bot.send_message(
                                    chat_id=user_id,
                                    text="ℹ️ Failed to upload a part of the discography. Please try again later."
                                )
                                all_success = False
                                
                            if os.path.exists(zip_path):
                                os.remove(zip_path)
                                
                        if all_success:
                            shutil.rmtree(download_dir, ignore_errors=True)
                        else:
                            # Do not fall back to sending individual tracks for discographies
                            pass
                    else:
                        logger.info(f"Creating ZIP for {content_type} {deezer_id}")
                        import asyncio
                        zip_success, zip_path = await asyncio.to_thread(self.file_handler.zip_folder, download_dir, title)
                        if not zip_success:
                            return False, "❌ Failed to create ZIP archive."
                            
                        document = FSInputFile(zip_path)
                        music_channel_id = os.getenv('MUSIC_CHANNEL_ID')
                        channel_msg_id = None
                        file_id_to_send = document
    
                        if music_channel_id:
                            try:
                                channel_msg = await bot.send_document(
                                    chat_id=music_channel_id,
                                    document=document,
                                    caption=f"@Spotizer_bot 🎧\n📀 {display_title}"
                                )
                                channel_msg_id = channel_msg.message_id
                                file_id_to_send = channel_msg.document.file_id
                            except Exception as e:
                                logger.error(f"Failed to send to music channel: {e}")
    
                        sent_message = await bot.send_document(
                            chat_id=user_id, 
                            document=file_id_to_send, 
                            caption=f"@Spotizer_bot 🎧"
                        )
                        
                        await self.add_download(
                            user_id=user_id,
                            deezer_id=deezer_id,
                            content_type=content_type,
                            file_id=sent_message.document.file_id,
                            quality=quality,
                            url=url,
                            title=title,
                            artist=artist if content_type == 'album' else "Unknown",
                            album=title if content_type == 'album' else None,
                            channel_id=int(music_channel_id) if music_channel_id else None,
                            message_id=channel_msg_id
                        )
                        
                        # Cleanup ZIP and directory
                        if os.path.exists(zip_path):
                            os.remove(zip_path)
                        shutil.rmtree(download_dir, ignore_errors=True)
                else:
                    # If make_zip is false but it's an album/playlist, we send tracks individually
                    # Generate an M3U playlist as well
                    musics_playlist = []
                    for t in result.tracks:
                        # Send track
                        audio_file = FSInputFile(t.file_path)
                        sent_message = await bot.send_audio(
                            chat_id=user_id,
                            audio=audio_file,
                            caption=f"@Spotizer_bot 🎧",
                            duration=t.duration,
                            title=t.title,
                            performer=t.artist
                        )
                        # Assume track_id is embedded in filename or just use deezer_id as placeholder
                        await self.add_download(
                            user_id=user_id,
                            deezer_id=deezer_id, # Can't easily get individual track ID here, use album ID
                            content_type='track',
                            file_id=sent_message.audio.file_id,
                            quality=quality,
                            url=url,
                            title=t.title,
                            artist=t.artist,
                            duration=t.duration,
                            file_name=os.path.basename(t.file_path),
                            album=t.album
                        )
                        musics_playlist.append((t.title, t.duration or 0, os.path.basename(t.file_path)))
                        
                    # Create M3U
                    if len(musics_playlist) > 1:
                        filename = f'deezer_{deezer_id}.m3u'
                        await self.file_handler.playlist_creator(musics_playlist, filename)
                        await bot.send_document(
                            chat_id=user_id,
                            document=FSInputFile(filename),
                            caption="<a href='https://telegra.ph/How-to-Use-M3U-Playlists-03-02'>What is this and how can I use it?</a>\n\n@Spotizer_bot 🎧",
                            parse_mode='HTML'
                        )
                        if os.path.exists(filename):
                            os.remove(filename)
                            
                    shutil.rmtree(download_dir, ignore_errors=True)

            else:
                # Single track download
                if not result.tracks:
                    return False, "❌ Track failed to download."
                
                track = result.tracks[0]
                audio_file = FSInputFile(track.file_path)
                
                music_channel_id = os.getenv('MUSIC_CHANNEL_ID')
                channel_msg_id = None
                file_id_to_send = audio_file

                if music_channel_id:
                    try:
                        channel_msg = await bot.send_audio(
                            chat_id=music_channel_id,
                            audio=audio_file,
                            caption=f"@Spotizer_bot 🎧\n{track.title} - {track.artist}",
                            duration=track.duration,
                            title=track.title,
                            performer=track.artist
                        )
                        channel_msg_id = channel_msg.message_id
                        file_id_to_send = channel_msg.audio.file_id
                    except Exception as e:
                        logger.error(f"Failed to send to music channel: {e}")

                sent_message = await bot.send_audio(
                    chat_id=user_id,
                    audio=file_id_to_send,
                    caption=f"@Spotizer_bot 🎧",
                    duration=track.duration,
                    title=track.title,
                    performer=track.artist,
                )

                await self.add_track(
                    track_id=str(deezer_id),
                    url=url,
                    file_id=sent_message.audio.file_id,
                    title=track.title,
                    artist=track.artist,
                    album=track.album,
                    duration=track.duration,
                    quality=quality,
                    channel_id=int(music_channel_id) if music_channel_id else None,
                    message_id=channel_msg_id,
                    spotify_id=None,
                )
                
                download_id = await self.add_download(
                    user_id=user_id,
                    deezer_id=deezer_id,
                    content_type='track',
                    file_id=sent_message.audio.file_id,
                    quality=quality,
                    url=url,
                    title=track.title,
                    artist=track.artist,
                    duration=track.duration,
                    file_name=os.path.basename(track.file_path),
                    album=track.album,
                    channel_id=int(music_channel_id) if music_channel_id else None,
                    message_id=channel_msg_id
                )
                
                await sent_message.edit_reply_markup(
                    reply_markup=MusicView.get_rating_keyboard(download_id)
                )
                
                # Cleanup track directory
                download_dir = os.path.dirname(track.file_path)
                shutil.rmtree(download_dir, ignore_errors=True)

            return True, "Download completed successfully"

        except Exception as e:
            logger.error(f"Download processing error: {str(e)}", exc_info=True)
            await bot.send_message(
                chat_id=user_id,
                text="An unexpected error occurred. Please try again later."
            )
            return False, "An error occurred while processing your download request."

    @staticmethod
    async def get_user_downloads(user_id, limit=5, offset=0):
        """Get user's download history."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserDownload)
                .where(UserDownload.user_id == user_id)
                .order_by(UserDownload.downloaded_at.desc())
                .offset(offset)
                .limit(limit)
            )
            downloads = result.scalars().all()
            return True, downloads

    @staticmethod
    async def update_download_rating(user_id: int, download_id: int, rating: int) -> tuple[bool, str]:
        """Update rating for a download."""
        async with async_session_maker() as session:
            async with session.begin():
                result = await session.execute(
                    select(UserDownload).where(
                        UserDownload.download_id == download_id,
                        UserDownload.user_id == user_id
                    )
                )
                download = result.scalars().first()
                if download:
                    download.user_rating = rating if rating != 0 else None
                    return True, "Rating updated"
                return False, "Download not found"
