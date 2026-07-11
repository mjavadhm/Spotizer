import os
import re
from sqlalchemy.future import select
from sqlalchemy.sql import func

from bale_bot.database import bale_async_session_maker
from bale_bot.database.models import BaleUserDownload
from bale_bot.controllers.user_controller import BaleUserController
from services.deezer_service import DeezerService, DeezerAPIClient
from utils.file_handler import FileHandler
from utils.url_validator import URLValidator
from bale_bot.views.music_view import MusicView
from bale_bot.bot import bot
from logger import get_logger

logger = get_logger(__name__)


class BaleDownloadController:
    """
    Download controller for Bale bot.
    Key difference from Telegram: No file caching - always download and send fresh files.
    """
    
    def __init__(self):
        self.deezer_service = DeezerService()
        self.file_handler = FileHandler()
        self.url_validator = URLValidator()
        logger.info("BaleDownloadController initialized")

    @staticmethod
    async def add_download(user_id, deezer_id, content_type, quality, url, title, artist, album, duration=None, file_name=None):
        """Add a download to the database. Returns download_id for rating buttons.
        Note: For Bale, we don't store file_id since it's Telegram-specific."""
        async with bale_async_session_maker() as session:
            # Check if this download already exists
            result = await session.execute(
                select(BaleUserDownload).where(
                    BaleUserDownload.user_id == user_id,
                    BaleUserDownload.deezer_id == deezer_id,
                    BaleUserDownload.content_type == content_type,
                    BaleUserDownload.quality == quality
                )
            )
            existing = result.scalars().first()
            
            if existing:
                # Update timestamp for existing download
                existing.downloaded_at = func.now()
                await session.commit()
                return existing.download_id
            
            # Insert new download (file_id is None for Bale)
            download = BaleUserDownload(
                user_id=user_id,
                deezer_id=deezer_id,
                content_type=content_type,
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

    async def process_download_request(self, user_id, url):
        """Process download request from user"""
        try:
            logger.info(f"Processing download request for user {user_id} - URL: {url}")
            
            if not self.url_validator.is_valid_url(url):
                logger.error(f"Invalid URL format provided by user {user_id}: {url}")
                return False, "Invalid URL format. Please provide a valid Deezer link."

            if "spotify" in url.lower():
                logger.warning(f"User {user_id} tried to download a Spotify link: {url}")
                return False, "❌ Spotify links are no longer supported. Please use a Deezer link."

            from bale_bot.controllers.user_controller import BaleUserController
            success, user_settings = await BaleUserController.get_user_settings(user_id)
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

            logger.info(f"Downloading {content_type}: {deezer_id}")
            result = await self.deezer_service.download(url, quality_download=quality)
            
            if not result.success:
                return False, f"❌ Download failed: {result.error}"

            import shutil
            from bale_bot.app import bot

            # If it's an album or playlist, we can optionally zip it
            if result.is_album_or_playlist:
                if not result.tracks:
                    return False, "❌ Album/Playlist is empty or failed to download."
                
                download_dir = os.path.dirname(result.tracks[0].file_path)
                
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
                        zip_results = self.file_handler.zip_directories_chunked(download_dir, title, chunk_size=5)
                        if not zip_results:
                            return False, "❌ Failed to create ZIP archive or no files found."
                        
                        all_success = True
                        for zip_success, zip_path in zip_results:
                            if not zip_success:
                                all_success = False
                                continue
                            
                            zip_size = os.path.getsize(zip_path)
                            if zip_size > 40 * 1024 * 1024:
                                logger.info(f"ZIP file too large ({zip_size} bytes). Falling back to individual tracks for this chunk.")
                                await bot.send_message(
                                    chat_id=user_id,
                                    text="ℹ️ A part of the artist ZIP file is too large for Bale (Max 40MB). Sending individual tracks instead..."
                                )
                                all_success = False
                                if os.path.exists(zip_path):
                                    os.remove(zip_path)
                            else:
                                try:
                                    with open(zip_path, 'rb') as zip_file:
                                        await bot.send_document(
                                            chat_id=user_id, 
                                            document=zip_file, 
                                            caption=f"@Spotizer_bot 🎧\n📀 {display_title}"
                                        )
                                    await self.add_download(
                                        user_id=user_id,
                                        deezer_id=deezer_id,
                                        content_type=content_type,
                                        quality=quality,
                                        url=url,
                                        title=title,
                                        artist="Unknown",
                                        album=None,
                                        file_name=os.path.basename(zip_path)
                                    )
                                    if os.path.exists(zip_path):
                                        os.remove(zip_path)
                                except Exception as e:
                                    logger.error(f"Failed to send ZIP part: {str(e)}", exc_info=True)
                                    all_success = False
                                    if os.path.exists(zip_path):
                                        os.remove(zip_path)
                        
                        if all_success:
                            shutil.rmtree(download_dir, ignore_errors=True)
                        else:
                            make_zip = False
                    else:
                        logger.info(f"Creating ZIP for {content_type} {deezer_id}")
                        zip_success, zip_path = self.file_handler.zip_folder(download_dir, title)
                        if not zip_success:
                            return False, "❌ Failed to create ZIP archive."
                            
                        zip_size = os.path.getsize(zip_path)
                        if zip_size > 40 * 1024 * 1024:
                            logger.info(f"ZIP file too large ({zip_size} bytes). Falling back to individual tracks.")
                            await bot.send_message(
                                chat_id=user_id,
                                text="ℹ️ The album ZIP file is too large for Bale (Max 40MB). Sending individual tracks instead..."
                            )
                            if os.path.exists(zip_path):
                                os.remove(zip_path)
                            make_zip = False
                        else:
                            try:
                                with open(zip_path, 'rb') as zip_file:
                                    sent_message = await bot.send_document(
                                        chat_id=user_id, 
                                        document=zip_file, 
                                        caption=f"@Spotizer_bot 🎧\n📀 {display_title}"
                                    )
                                
                                await self.add_download(
                                    user_id=user_id,
                                    deezer_id=deezer_id,
                                    content_type=content_type,
                                    quality=quality,
                                    url=url,
                                    title=title,
                                    artist=artist if content_type == 'album' else "Unknown",
                                    album=title if content_type == 'album' else None,
                                    file_name=os.path.basename(zip_path)
                                )
                                
                                if os.path.exists(zip_path):
                                    os.remove(zip_path)
                                shutil.rmtree(download_dir, ignore_errors=True)
                            except Exception as e:
                                logger.error(f"Failed to send ZIP: {str(e)}", exc_info=True)
                                await bot.send_message(
                                    chat_id=user_id,
                                    text="ℹ️ Failed to send ZIP. Sending individual tracks instead..."
                                )
                                if os.path.exists(zip_path):
                                    os.remove(zip_path)
                                make_zip = False

                if not make_zip:
                    musics_playlist = []
                    for t in result.tracks:
                        with open(t.file_path, 'rb') as audio_file:
                            try:
                                sent_message = await bot.send_audio(
                                    chat_id=user_id,
                                    audio=audio_file,
                                    caption=f"@Spotizer_bot 🎧",
                                    duration=t.duration,
                                    title=t.title
                                )
                                
                                await self.add_download(
                                    user_id=user_id,
                                    deezer_id=deezer_id, 
                                    content_type='track',
                                    quality=quality,
                                    url=url,
                                    title=t.title,
                                    artist=t.artist,
                                    duration=t.duration,
                                    file_name=os.path.basename(t.file_path),
                                    album=t.album
                                )
                            except Exception as track_err:
                                logger.error(f"Error sending track {t.title}: {str(track_err)}")
                                
                        musics_playlist.append((t.title, t.duration, os.path.basename(t.file_path)))
                        if os.path.exists(t.file_path):
                            os.remove(t.file_path)

                    if len(musics_playlist) > 1:
                        filename = f'deezer_{deezer_id}.m3u'
                        await self.file_handler.playlist_creator(musics_playlist, filename)
                        
                        try:
                            with open(filename, 'rb') as playlist_file:
                                await bot.send_document(
                                    chat_id=user_id,
                                    document=playlist_file,
                                    caption="<a href='https://telegra.ph/How-to-Use-M3U-Playlists-03-02'>What is this and how can I use it?</a>\n\n@Spotizer_bot 🎧",
                                )
                        except Exception:
                            pass
                            
                        if os.path.exists(filename):
                            os.remove(filename)
                            
                    shutil.rmtree(download_dir, ignore_errors=True)
                else:
                    musics_playlist = []
                    for t in result.tracks:
                        with open(t.file_path, 'rb') as audio_file:
                            sent_message = await bot.send_audio(
                                chat_id=user_id,
                                audio=audio_file,
                                caption=f"@Spotizer_bot 🎧",
                                duration=t.duration,
                                title=t.title)
                        
                        await self.add_download(
                            user_id=user_id,
                            deezer_id=deezer_id, 
                            content_type='track',
                            quality=quality,
                            url=url,
                            title=t.title,
                            artist=t.artist,
                            duration=t.duration,
                            file_name=os.path.basename(t.file_path),
                            album=t.album
                        )
                        musics_playlist.append((t.title, t.duration, os.path.basename(t.file_path)))
                        if os.path.exists(t.file_path):
                            os.remove(t.file_path)

                    if len(musics_playlist) > 1:
                        filename = f'deezer_{deezer_id}.m3u'
                        await self.file_handler.playlist_creator(musics_playlist, filename)
                        
                        with open(filename, 'rb') as playlist_file:
                            await bot.send_document(
                                chat_id=user_id,
                                document=playlist_file,
                                caption="<a href='https://telegra.ph/How-to-Use-M3U-Playlists-03-02'>What is this and how can I use it?</a>\n\n@Spotizer_bot 🎧",
                            )
                        if os.path.exists(filename):
                            os.remove(filename)
                            
                    shutil.rmtree(download_dir, ignore_errors=True)
            else:
                if not result.tracks:
                    return False, "❌ Failed to download track."
                    
                t = result.tracks[0]
                with open(t.file_path, 'rb') as audio_file:
                    sent_message = await bot.send_audio(
                        chat_id=user_id,
                        audio=audio_file,
                        caption=f"@Spotizer_bot 🎧",
                        duration=t.duration,
                        title=t.title)
                
                await self.add_download(
                    user_id=user_id,
                    deezer_id=deezer_id,
                    content_type='track',
                    quality=quality,
                    url=url,
                    title=t.title,
                    artist=t.artist,
                    duration=t.duration,
                    file_name=os.path.basename(t.file_path),
                    album=t.album
                )
                
                if os.path.exists(t.file_path):
                    os.remove(t.file_path)

            return True, "Download completed successfully."
        except Exception as e:
            logger.error(f"Download processing error: {str(e)}", exc_info=True)
            try:
                from bale_bot.app import bot
                await bot.send_message(
                    chat_id=user_id,
                    text="An unexpected error occurred. Please try again later."
                )
            except:
                pass
            return False, "An error occurred while processing your download request."

    @staticmethod
    async def get_user_downloads(user_id, limit=5, offset=0):
        """Get user's download history."""
        async with bale_async_session_maker() as session:
            result = await session.execute(
                select(BaleUserDownload)
                .where(BaleUserDownload.user_id == user_id)
                .order_by(BaleUserDownload.downloaded_at.desc())
                .offset(offset)
                .limit(limit)
            )
            downloads = result.scalars().all()
            return True, downloads

    @staticmethod
    async def update_download_rating(user_id: int, download_id: int, rating: int) -> tuple[bool, str]:
        """
        Update rating for a download.
        Args:
            user_id: User's Bale ID
            download_id: ID of the download record
            rating: 1=like, -1=dislike, 0=remove rating
        Returns:
            tuple[bool, str]: Success status and message
        """
        async with bale_async_session_maker() as session:
            async with session.begin():
                result = await session.execute(
                    select(BaleUserDownload).where(
                        BaleUserDownload.download_id == download_id,
                        BaleUserDownload.user_id == user_id
                    )
                )
                download = result.scalars().first()
                if download:
                    download.user_rating = rating if rating != 0 else None
                    return True, "Rating updated"
                return False, "Download not found"

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
            logger.error(f"Error getting artist albums: {str(e)}", exc_info=True)
            return []
