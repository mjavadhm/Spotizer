import os
import logging
import requests
from deezloader.deezloader import DeeLogin
import re
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from utils.file_handler import FileHandler
from deezloader.models.smart import Smart


logger = logging.getLogger(__name__)
arl = os.getenv('DEEZER_ARL')
deedownload = DeeLogin(arl="4f843574c19f3063f060c139878478063249e932b57d5f653f14dbee898dd5430b79e71e166324ade5e44fa3e41dc6d4e8f593ea67451e3d20933d71ca45c32401942d18ee623f6c5bc75416d9d634afd4998659d167cc0dae05d2d08f17c05b")
@dataclass
class DownloadResult:
    success: bool
    track_info: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    error: Optional[str] = None

class DeezerService:
    def __init__(self):
        self.file_handler = FileHandler()
    
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
