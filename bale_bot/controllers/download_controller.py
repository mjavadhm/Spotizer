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
                file_id=None,  # Not used for Bale
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
        """
        Process download request from user.
        For Bale: Always download fresh - no file_id caching.
        """
        try:
            logger.info(f"Processing download request for user {user_id} - URL: {url}")
            
            if not self.url_validator.is_valid_url(url):
                logger.error(f"Invalid URL format provided by user {user_id}: {url}")
                return False, "Invalid URL format. Please provide a valid Deezer or Spotify link."

            # Get user settings
            success, user_settings = await BaleUserController.get_user_settings(user_id)
            if not success:
                quality = 'MP3_320'
                make_zip = True
            else:
                quality = user_settings.get('download_quality', 'MP3_320')
                make_zip = user_settings.get('make_zip', True)
            logger.info(f"User {user_id} settings - Quality: {quality}, Make ZIP: {make_zip}")

            if "spotify" in url.lower():
                logger.error(f"Spotify link rejected: {url}")
                return False, "❌ Spotify links are no longer supported. Please use a Deezer link."

            content_type, deezer_id = self.deezer_service.extract_info_from_url(url)
            logger.info(f"Extracted info - Type: {content_type}, ID: {deezer_id}")
            
            if not content_type or not deezer_id:
                logger.error(f"Could not extract content type or ID from URL: {url}")
                return False, "❌ Invalid URL format. Please provide a valid Deezer or Spotify link."

            # For Bale: Always download fresh, no caching
            if make_zip and 'track' not in url:
                logger.info(f"Downloading {content_type} as ZIP: {deezer_id}")
                smart = await self.deezer_service.download(url, quality_download=quality, make_zip=True)
                
                if smart.album:
                    logger.info(f"Processing album download: {smart.album.title}")
                    file_path = smart.album.zip_path
                    
                    # Send document to user (always fresh, no caching)
                    await bot.send_document(
                        chat_id=user_id, 
                        document=open(file_path, 'rb'),
                        caption=f"@Spotizer_bot 🎧"
                    )
                    
                    await self.add_download(
                        user_id=user_id,
                        deezer_id=deezer_id,
                        content_type='album',
                        quality=quality,
                        url=url,
                        title=smart.album.title,
                        artist=smart.album.artist,
                        album=smart.album.title,
                    )
                    
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Deleted album ZIP file: {file_path}")
                    
                elif smart.playlist:
                    logger.info(f"Processing playlist download: {smart.playlist.title}")
                    file_path = smart.playlist.zip_path
                    
                    # Send document to user
                    await bot.send_document(
                        chat_id=user_id, 
                        document=open(file_path, 'rb'),
                        caption=f"@Spotizer_bot 🎧"
                    )
                    
                    await self.add_download(
                        user_id=user_id,
                        deezer_id=deezer_id,
                        content_type='playlist',
                        quality=quality,
                        url=url,
                        title=smart.playlist.title,
                        artist=smart.playlist.artist,
                        album=None,
                    )
                    
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Deleted playlist ZIP file: {file_path}")
            else:
                logger.info(f"Processing individual tracks for {content_type} {deezer_id}")
                track_ids = await self.deezer_service.get_track_list(content_type, deezer_id)
                musics_playlist = []
                
                for track_id in track_ids:
                    try:
                        logger.info(f"Processing track: {track_id}")
                        
                        # For Bale: Always download fresh
                        track_link = f"https://www.deezer.com/track/{track_id}"
                        logger.info(f"Downloading track: {track_link}")
                        smart = await self.deezer_service.download(track_link, quality_download=quality, make_zip=False)
                        
                        if smart.track:
                            file_path = smart.track.song_path
                            try:
                                duration = self.file_handler.get_audio_duration(file_path)
                                
                                title = smart.track.music if hasattr(smart.track, "music") else f"Track {track_id}"
                                artist = smart.track.artist if hasattr(smart.track, "artist") else "Unknown Artist"
                                album = smart.track.album if hasattr(smart.track, "album") else "Unknown Album"

                                # Send audio to user (always fresh file)
                                with open(file_path, 'rb') as audio_file:
                                    await bot.send_audio(
                                        chat_id=user_id,
                                        audio=audio_file,
                                        caption=f"@Spotizer_bot 🎧",
                                        duration=duration,
                                        title=title,
                                        performer=artist,
                                    )

                                download_id = await self.add_download(
                                    user_id=user_id,
                                    deezer_id=track_id,
                                    content_type='track',
                                    quality=quality,
                                    url=track_link,
                                    title=title,
                                    artist=artist,
                                    duration=duration,
                                    file_name=os.path.basename(file_path),
                                    album=album,
                                )
                                
                                musics = (title, duration, os.path.basename(file_path))
                                musics_playlist.append(musics)
                            except Exception as e:
                                logger.error(f"Download processing error: {str(e)}", exc_info=True)
                                await bot.send_message(
                                    chat_id=user_id,
                                    text="An error occurred while processing your download request."
                                )
                            finally:
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                                    logger.info(f"Deleted track file: {file_path}")
                    except Exception as e:
                        await bot.send_message(
                            chat_id=user_id,
                            text=f"❌ Track 'https://www.deezer.com/us/track/{track_id}' isn't in Deezer or not available for download.",
                        )
                        logger.error(f"Error processing track {track_id}: {str(e)}", exc_info=True)

                if len(musics_playlist) > 1:
                    filename = f'deezer_{deezer_id}.m3u'
                    logger.info(f"Creating playlist file: {filename}")
                    await self.file_handler.playlist_creator(musics_playlist, filename)
                    
                    with open(filename, 'rb') as playlist_file:
                        await bot.send_document(
                            chat_id=user_id,
                            document=playlist_file,
                            caption="<a href='https://telegra.ph/How-to-Use-M3U-Playlists-03-02'>What is this and how can I use it?</a>\n\n@Spotizer_bot 🎧",
                        )
                    
                    if os.path.exists(filename):
                        os.remove(filename)
                        logger.info(f"Deleted playlist file: {filename}")

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
