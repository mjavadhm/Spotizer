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

    async def process_download_request(self, user_id, url):
        """Process download request from user"""
        try:
            logger.info(f"Processing download request for user {user_id} with URL: {url}")
            
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
            logger.info(f"Extracted info - Type: {content_type}, Deezer ID: {deezer_id}")

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
                        artist=smart.album.artist
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
                        artist=smart.playlist.artist
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
                                file_name=sent_message.audio.file_name
                            )
                            
                            musics = (title, duration, sent_message.audio.file_name)
                            musics_playlist.append(musics)
                            
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
