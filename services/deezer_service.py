import os
import logging
import requests
from deezloader.deezloader import DeeLogin
import re
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from utils.file_handler import FileHandler
from typing import Optional
# from deezloader.model.smart import Smart
class Track:
    def __init__(
        self,
        tags: dict,
        song_path: str,
        file_format: str,
        quality: str,
        link: str,
        ids: int
    ) -> None:
        self.tags = tags
        self.__set_tags()
        self.song_name = f"{self.title} - {self.artist}"
        self.song_path = song_path
        self.file_format = file_format
        self.quality = quality
        self.link = link
        self.ids = ids
        self.md5_image = None
        self.success = True
        self.__set_track_md5()

    def __set_tags(self):
        for tag, value in self.tags.items():
            setattr(
                self, tag, value
            )

    def __set_track_md5(self):
        self.track_md5 = f"track/{self.ids}"

    def set_fallback_ids(self, fallback_ids):
        self.fallback_ids = fallback_ids
        self.fallback_track_md5 = f"track/{self.fallback_ids}"


class Album:
    def __init__(self, ids: int) -> None:
        self.tracks: list[Track] = []
        self.zip_path = None
        self.image = None
        self.album_quality = None
        self.md5_image = None
        self.ids = ids
        self.nb_tracks = None
        self.title = None
        self.artist = None
        self.upc = None
        self.tags = None
        self.__set_album_md5()

    def __set_album_md5(self):
        self.album_md5 = f"album/{self.ids}"


class Playlist:
    def __init__(self, ids: int) -> None:
        self.tracks: list[Track] = []
        self.zip_path = None
        self.ids = ids
        self.title = None


class Smart:
    def __init__(self) -> None:
        self.track: Optional[Track] = None
        self.album: Optional[Album] = None
        self.playlist: Optional[Playlist] = None
        self.type = None
        self.source = None


logger = logging.getLogger(__name__)
arl = os.getenv('DEEZER_ARL')
deedownload = DeeLogin(arl=arl)
@dataclass
class DownloadResult:
    success: bool
    track_info: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    error: Optional[str] = None

class DeezerService:
    def __init__(self):
        self.file_handler = FileHandler()
    
        if not self.arl:
            logger.error("DEEZER_ARL environment variable is not set")
        elif len(self.arl) < 100:  # ARL tokens are typically longer than 100 characters
            logger.error("DEEZER_ARL token appears to be invalid or truncated")
        self.download_url = "https://api.deezer.com/track/{track_id}/download"

    async def download(self, url: str, output_folder="downloads", quality_download: str = 'MP3_320', make_zip: bool = False) -> Smart:
        """Download track/album/playlist from Deezer"""
        try:

            content_type, deezer_id = self.extract_info_from_url(url)
            if not content_type or not deezer_id:
                return DownloadResult(False, error="Invalid Deezer URL")


            # Download file
            smart = deedownload.download_smart(url, output_folder, quality_download="MP3_320", make_zip=make_zip)
            return smart


        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            return False

    def extract_info_from_url(self, url: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract content type and ID from Deezer URL"""
        patterns = {
            'track': r'deezer\.com(?:\/[a-z]{2})?\/track\/(\d+)',
            'album': r'deezer\.com(?:\/[a-z]{2})?\/album\/(\d+)',
            'playlist': r'deezer\.com(?:\/[a-z]{2})?\/playlist\/(\d+)'
        }
        
        for content_type, pattern in patterns.items():
            match = re.search(pattern, url)
            if match:
                return content_type, int(match.group(1))
        return None, None

    def get_deezer_info(content_type, deezer_id):
        url = f"https://api.deezer.com/{content_type}/{deezer_id}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"خطا در گرفتن اطلاعات از Deezer: {response.status_code}")
    
    # async def download_file(self, track_info: Dict[str, Any], quality: str) -> Optional[str]:
    #     """Download audio file with specified quality"""
    #     try:
    #         track_id = track_info['id']
    #         # Use direct stream URL instead of download endpoint
    #         stream_url = f"https://api.deezer.com/track/{track_id}/stream"
            
    #         headers = {
    #             'User-Agent': 'Mozilla/5.0',
    #             'Cookie': f'arl={self.arl}'
    #         }
            
    #         # Add quality parameter if specified
    #         params = {}
    #         if quality and quality.upper() in ['MP3_320', 'MP3_128', 'FLAC']:
    #             params['format'] = quality.lower().replace('mp3_', '')
            
    #         response = requests.get(stream_url, headers=headers, params=params, stream=True)
    #         if response.status_code != 200:
    #             logger.error(f"Download failed. Status code: {response.status_code}")
    #             if response.status_code == 403:
    #                 logger.error("Authentication failed. Please check your Deezer ARL token.")
    #             return None
            
    #         # Check if response is valid audio
    #         content_type = response.headers.get('content-type', '')
    #         if not content_type.startswith('audio/'):
    #             logger.error(f"Invalid content type received: {content_type}")
    #             return None
            
    #         # Create filename from track info
    #         artist_name = track_info.get('artist', {}).get('name', 'Unknown Artist')
    #         title = track_info.get('title', 'Unknown Title')
    #         filename = f"{artist_name} - {title}.mp3"
            
    #         # Save the file
    #         success, file_path = await self.file_handler.save_audio_file(response.content, filename)
    #         if not success:
    #             logger.error("Failed to save audio file")
    #             return None
            
    #         # Verify file was saved and is valid
    #         if not os.path.exists(file_path):
    #             logger.error("File was not saved successfully")
    #             return None
            
    #         if not self.file_handler.is_valid_audio_file(file_path):
    #             logger.error("Downloaded file is not a valid audio file")
    #             os.remove(file_path)  # Clean up invalid file
    #             return None
                
    #         return file_path
            
    #     except Exception as e:
    #         logger.error(f"Error downloading file: {str(e)}")
    #         return None

    async def create_zip(self, file_path: str, title: str) -> Optional[str]:
        """Create ZIP archive for album/playlist"""
        try:
            success, zip_path = self.file_handler.create_zip_archive([file_path], f"{title}.zip")
            return zip_path if success else None
        except Exception as e:
            logger.error(f"Error creating ZIP: {str(e)}")
            return None
    
    
    async def get_track_list(self, content_type, deezer_id):
        if content_type == 'track':
            return [deezer_id]  # برای ترک تکی، فقط همون شناسه رو برمی‌گردونه
        elif content_type == 'album':
            album_info = self.get_deezer_info('album', deezer_id)
            return [track['id'] for track in album_info['tracks']['data']]
        elif content_type == 'playlist':
            playlist_info = self.get_deezer_info('playlist', deezer_id)
            return [track['id'] for track in playlist_info['tracks']['data']]
        else:
            raise ValueError(f"نوع محتوا اشتباهه: {content_type}")
