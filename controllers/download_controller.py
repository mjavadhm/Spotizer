import aiogram
import os
from sqlalchemy.future import select
from database.session import async_session_maker
from controllers.user_controller import UserController
from models.base import User, UserSettings, UserDownload, Track
from services.deezer_service import DeezerService
from services.spotify_service import SpotifyService
from utils.file_handler import FileHandler
from utils.url_validator import URLValidator
from aiogram.types import FSInputFile
from bot import bot
from logger import get_logger

logger = get_logger(__name__)

class DownloadController:
    def __init__(self):
        self.deezer_service = DeezerService()
        self.spotify_service = SpotifyService()
        self.file_handler = FileHandler()
        self.url_validator = URLValidator()
        logger.info("DownloadController initialized")

    @staticmethod
    async def add_download(user_id, deezer_id, content_type, file_id, quality, url, title, artist, album, duration=None, file_name=None):
        """Add a download to the database."""
        async with async_session_maker() as session:
            async with session.begin():
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

    @staticmethod
    async def get_track(track_id):
        """Get a track from the database."""
        async with async_session_maker() as session:
            return await session.get(Track, track_id)

    @staticmethod
    async def add_track(track_id, url, file_id, title, artist, album, duration):
        """Add a track to the database."""
        async with async_session_maker() as session:
            async with session.begin():
                track = Track(
                    track_id=track_id,
                    url=url,
                    file_id=file_id,
                    title=title,
                    artist=artist,
                    album=album,
                    duration=duration,
                )
                session.add(track)
            await session.commit()
    async def search(self, query: str, search_type: str, page: int = 1) -> tuple[bool, list]:
        """
        Search for music content on Spotify
        
        Args:
            query (str): Search query
            search_type (str): Type of content to search for ('track', 'album', 'playlist')
            page (int): Page number for pagination (default: 1)
            
        Returns:
            tuple[bool, list]: Success status and list of search results
        """
        try:
            logger.info(f"Searching for {search_type}s with query: {query} (Page: {page})")
            
            # Calculate offset for pagination (5 items per page)
            offset = (page - 1) * 5
            
            # Perform search using spotify service
            results = await self.spotify_service.search(query, search_type, limit=5, offset=offset)
            
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
        """
        Get detailed information about a music item
        
        Args:
            content_type (str): Type of content ('track', 'album', 'playlist')
            item_id (str): Spotify ID of the item
            
        Returns:
            tuple[bool, dict]: Success status and item information
        """
        try:
            logger.info(f"Getting info for {content_type} with ID: {item_id}")
            
            item_info = await self.spotify_service.get_item_info(content_type, item_id)
            
            if item_info:
                logger.info(f"Successfully retrieved info for {content_type} {item_id}")
                return True, item_info
            else:
                logger.warning(f"No info found for {content_type} {item_id}")
                return False, {}
                
        except Exception as e:
            logger.error(f"Error getting item info for {content_type} {item_id}: {str(e)}", exc_info=True)
            return False, {}

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
                return False, "Invalid URL format. Please provide a valid Deezer or Spotify link."

            # Get user settings
            success, user_settings = await UserController.get_user_settings(user_id)
            if not success:
                # Handle case where user settings are not found
                quality = 'MP3_320'
                make_zip = True
            else:
                quality = user_settings.get('download_quality', 'MP3_320')
                make_zip = user_settings.get('make_zip', True)
            logger.info(f"User {user_id} settings - Quality: {quality}, Make ZIP: {make_zip}")

            # Convert Spotify URL to Deezer if needed
            if "spotify" in url:
                if 'playlist' in url:
                    logger.error(f"Spotify playlist not supported: {url}")
                    return False, "Spotify playlists are not supported yet. Please use a Deezer link."
                logger.info(f"Converting Spotify URL to Deezer URL: {url}")
                url = self.deezer_service.convert_to_deezer(url)
                logger.info(f"Converted to Deezer URL: {url}")

            content_type, deezer_id = self.deezer_service.extract_info_from_url(url)
            logger.info(f"Extracted info - Type: {content_type}, ID: {deezer_id}")

            if make_zip and 'track' not in url:
                existing_zip = await self.get_track_by_deezer_id_quality(user_id, deezer_id, quality)
                if existing_zip:
                    logger.info(f"Found existing ZIP for {content_type} {deezer_id}")
                    await bot.send_document(
                        chat_id=user_id,
                        document=existing_zip.file_id,
                        caption=f"@Spotizer_bot 🎧"
                    )
                    return True, "Sent existing ZIP file"

                logger.info(f"Downloading {content_type} as ZIP: {deezer_id}")
                smart = await self.deezer_service.download(url, quality_download=quality, make_zip=True)
                
                if smart.album:
                    logger.info(f"Processing album download: {smart.album.title}")
                    file_path = smart.album.zip_path
                    document = FSInputFile(file_path)
                    sent_message = await bot.send_document(
                        chat_id=user_id, 
                        document=document, 
                        caption=f"@Spotizer_bot 🎧"
                    )
                    
                    await self.add_download(
                        user_id=user_id,
                        deezer_id=deezer_id,
                        content_type='album',
                        file_id=sent_message.document.file_id,
                        quality=quality,
                        url=url,
                        title=smart.album.title,
                        artist=smart.album.artist,
                        album=smart.album.title
                    )
                    
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Deleted album ZIP file: {file_path}")
                    
                elif smart.playlist:
                    logger.info(f"Processing playlist download: {smart.playlist.title}")
                    file_path = smart.playlist.zip_path
                    document = FSInputFile(file_path)
                    sent_message = await bot.send_document(
                        chat_id=user_id, 
                        document=document, 
                        caption=f"@Spotizer_bot 🎧"
                    )
                    
                    await self.add_download(
                        user_id=user_id,
                        deezer_id=deezer_id,
                        content_type='playlist',
                        file_id=sent_message.document.file_id,
                        quality=quality,
                        url=url,
                        title=smart.playlist.title,
                        artist=smart.playlist.artist,
                        album='album.title'
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
                        track = await self.get_track(track_id)
                        if track:
                            logger.info(f"Found cached track: {track.title}")
                            await bot.send_audio(
                                chat_id=user_id,
                                audio=track.file_id,
                                caption=f"@Spotizer_bot 🎧",
                                title=track.title,
                                performer=track.artist,
                            )
                            await self.add_download(
                                user_id=user_id,
                                deezer_id=track_id,
                                content_type="track",
                                file_id=track.file_id,
                                quality=quality,
                                url=track.url,
                                title=track.title,
                                artist=track.artist,
                                duration=track.duration,
                                file_name=None, # Or retrieve if available
                                album=track.album,
                            )
                            musics = (track.title, track.duration, None)
                            musics_playlist.append(musics)
                        else:
                            track_link = f"https://www.deezer.com/track/{track_id}"
                            logger.info(f"Downloading new track: {track_link}")
                            smart = await self.deezer_service.download(track_link, quality_download=quality, make_zip=False)
                            
                            if smart.track:
                                file_path = smart.track.song_path
                                try:
                                    audio_file = FSInputFile(file_path)
                                    duration = self.file_handler.get_audio_duration(file_path)
                                    
                                    title = smart.track.music if hasattr(smart.track, "music") else f"Track {track_id}"
                                    artist = smart.track.artist if hasattr(smart.track, "artist") else "Unknown Artist"
                                    album = smart.track.album if hasattr(smart.track, "album") else "Unknown Album"

                                    sent_message = await bot.send_audio(
                                        chat_id=user_id,
                                        audio=audio_file,
                                        caption=f"@Spotizer_bot 🎧",
                                        duration=duration,
                                        title=title,
                                        performer=artist,
                                    )

                                    await self.add_track(
                                        track_id=track_id,
                                        url=track_link,
                                        file_id=sent_message.audio.file_id,
                                        title=title,
                                        artist=artist,
                                        album=album,
                                        duration=duration,
                                    )
                                    
                                    await self.add_download(
                                        user_id=user_id,
                                        deezer_id=track_id,
                                        content_type='track',
                                        file_id=sent_message.audio.file_id,
                                        quality=quality,
                                        url=track_link,
                                        title=title,
                                        artist=artist,
                                        duration=duration,
                                        file_name=sent_message.audio.file_name,
                                        album=album
                                    )
                                    
                                    musics = (title, duration, sent_message.audio.file_name)
                                    musics_playlist.append(musics)
                                except Exception as e:
                                    logger.error(f"Download processing error: {str(e)}", exc_info=True)
                                    return False, "An error occurred while processing your download request."
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
                        # return False, "An error occurred while processing your download request."

                if len(musics_playlist) > 1:
                    filename = f'deezer_{deezer_id}.m3u'
                    logger.info(f"Creating playlist file: {filename}")
                    await self.file_handler.playlist_creator(musics_playlist, filename)
                    
                    await bot.send_document(
                        chat_id=user_id,
                        document=FSInputFile(filename),
                        caption="<a href='https://telegra.ph/How-to-Use-M3U-Playlists-03-02'>What is this and how can I use it?</a>\n\n@Spotizer_bot 🎧",
                        parse_mode='HTML'
                    )
                    
                    if os.path.exists(filename):
                        os.remove(filename)
                        logger.info(f"Deleted playlist file: {filename}")

            return True, "Download completed successfully"

        except Exception as e:
            logger.error(f"Download processing error: {str(e)}", exc_info=True)
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

    async def get_artist_top_tracks(self, artist_id: str) -> list:
        """Get artist's top tracks"""
        try:
            logger.info(f"Getting top tracks for artist {artist_id}")
            top_tracks = self.spotify_service.sp.artist_top_tracks(artist_id)['tracks']
            processed_tracks = []
            for track in top_tracks:
                processed_tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'duration': self.spotify_service._format_duration(track['duration_ms'])
                })
            return processed_tracks
        except Exception as e:
            logger.error(f"Error getting artist top tracks: {str(e)}", exc_info=True)
            return []

    async def get_artist_albums(self, artist_id: str) -> list:
        """Get artist's albums"""
        try:
            logger.info(f"Getting albums for artist {artist_id}")
            albums = self.spotify_service.sp.artist_albums(artist_id, album_type='album')['items']
            processed_albums = []
            for album in albums:
                processed_albums.append({
                    'id': album['id'],
                    'name': album['name'],
                    'release_date': album['release_date']
                })
            return processed_albums
        except Exception as e:
            logger.error(f"Error getting artist albums: {str(e)}", exc_info=True)
            return []
