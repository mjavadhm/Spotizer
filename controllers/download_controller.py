import aiogram
import os
from models.download_model import DownloadModel
from models.user_model import UserModel
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
        self.download_model = DownloadModel()
        self.user_model = UserModel()
        self.deezer_service = DeezerService()
        self.spotify_service = SpotifyService()
        self.file_handler = FileHandler()
        self.url_validator = URLValidator()
        logger.info("DownloadController initialized")

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

    async def process_download_request(self, user_id, url):
        """Process download request from user"""
        try:
            logger.info(f"Processing download request for user {user_id} - URL: {url}")
            
            if not self.url_validator.is_valid_url(url):
                logger.error(f"Invalid URL format provided by user {user_id}: {url}")
                return False, "Invalid URL format. Please provide a valid Deezer or Spotify link."

            # Get user settings
            user_settings = self.user_model.get_user_settings(user_id)
            quality = user_settings.get('download_quality', 'MP3_320')
            make_zip = user_settings.get('make_zip', True)
            logger.info(f"User {user_id} settings - Quality: {quality}, Make ZIP: {make_zip}")

            # Convert Spotify URL to Deezer if needed
            if "spotify" in url:
                if 'playlist' in url:
                    logger.error(f"Spotify playlist not supported: {url}")
                    return False, "Spotify playlists are not supported yet. Please use a Deezer link."
                logger.info(f"Converting Spotify URL to Deezer URL: {url}")
                url = self.spotify_service.convert_to_deezer_url(url)
                logger.info(f"Converted to Deezer URL: {url}")

            content_type, deezer_id = self.deezer_service.extract_info_from_url(url)
            logger.info(f"Extracted info - Type: {content_type}, ID: {deezer_id}")

            if make_zip and 'track' not in url:
                existing_zip = await self.download_model.get_track_by_deezer_id_quality(user_id, deezer_id, quality)
                if existing_zip:
                    logger.info(f"Found existing ZIP for {content_type} {deezer_id}")
                    await bot.send_document(
                        chat_id=user_id,
                        document=existing_zip['file_id'],
                        caption=f"@Spotizer_bot 🎧"
                    )
                    return True, "Sent existing ZIP file"

                logger.info(f"Downloading {content_type} as ZIP: {deezer_id}")
                smart = self.deezer_service.download(url, quality_download=quality, make_zip=True)
                
                if smart.album:
                    logger.info(f"Processing album download: {smart.album.title}")
                    file_path = smart.album.zip_path
                    document = FSInputFile(file_path)
                    sent_message = await bot.send_document(
                        chat_id=user_id, 
                        document=document, 
                        caption=f"@Spotizer_bot 🎧"
                    )
                    
                    self.download_model.add_track(
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
                    
                    self.download_model.add_track(
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
                    logger.info(f"Processing track: {track_id}")
                    existing_track = self.download_model.get_track_by_deezer_id_quality(user_id, track_id, quality)
                    
                    if existing_track:
                        logger.info(f"Found existing track: {existing_track['title']}")
                        await bot.send_audio(
                            chat_id=user_id,
                            audio=existing_track['file_id'],
                            caption=f"@Spotizer_bot 🎧",
                            title=existing_track['title'],
                            performer=existing_track['artist']
                        )
                        musics = (existing_track['title'], existing_track['duration'], existing_track['file_name'])
                        musics_playlist.append(musics)
                    else:
                        track_link = f"https://www.deezer.com/track/{track_id}"
                        logger.info(f"Downloading new track: {track_link}")
                        smart = await self.deezer_service.download(url, quality_download=quality, make_zip=False)
                        
                        if smart.track:
                            file_path = smart.track.song_path
                            try:
                                audio_file = FSInputFile(file_path)
                                duration = self.file_handler.get_audio_duration(file_path)
                                
                                title = None
                                if hasattr(smart.track, 'music'):
                                    title = smart.track.music
                                    logger.info(f"Track title: {title}")
                                else:
                                    logger.warning(f"Title not found for track {track_id}, using default")
                                    title = f"Track {track_id}"
                                
                                artist = None
                                if hasattr(smart.track, 'artist'):
                                    artist = smart.track.artist
                                else:
                                    logger.warning(f"Artist not found for track {track_id}, using default")
                                    artist = "Unknown Artist"

                                sent_message = await bot.send_audio(
                                    chat_id=user_id,
                                    audio=audio_file,
                                    caption=f"@Spotizer_bot 🎧",
                                    duration=duration,
                                    title=title,
                                    performer=artist
                                )
                                
                                self.download_model.add_track(
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
                                    album=None
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

    async def get_user_downloads(self, user_id, limit=5):
        """Get user's download history"""
        try:
            logger.info(f"Fetching download history for user {user_id} (limit: {limit})")
            downloads = self.download_model.get_user_downloads(user_id, limit)
            return True, downloads
        except Exception as e:
            logger.error(f"Error fetching download history: {str(e)}", exc_info=True)
            return False, "Could not retrieve download history."

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

