import os
import requests
import re
from deezloader.deezloader import DeeLogin
from deezloader.models.smart import Smart
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from utils.file_handler import FileHandler
from logger import get_logger

logger = get_logger(__name__)

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
        logger.info("DeezerService initialized")
    
    async def download(self, url: str, output_folder="downloads", quality_download: str = 'MP3_320', make_zip: bool = False) -> Smart:
        """Download track/album/playlist from Deezer"""
        try:
            logger.info(f"Starting download - URL: {url}, Quality: {quality_download}, Make ZIP: {make_zip}")
            content_type, deezer_id = self.extract_info_from_url(url)
            
            if not content_type or not deezer_id:
                logger.error(f"Invalid Deezer URL provided: {url}")
                return DownloadResult(False, error="Invalid Deezer URL")

            logger.info(f"Downloading {content_type} with ID: {deezer_id}")
            smart = deedownload.download_smart(url, output_folder, quality_download=quality_download, make_zip=make_zip)
            logger.info(f"Successfully downloaded {content_type} - ID: {deezer_id}")
            return smart

        except Exception as e:
            logger.error(f"Download error for URL {url}: {str(e)}", exc_info=True)
            return False

    def extract_info_from_url(self, url: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract content type and ID from Deezer URL"""
        try:
            logger.info(f"Extracting info from URL: {url}")
            patterns = {
                'track': r'deezer\.com(?:\/[a-z]{2})?\/track\/(\d+)',
                'album': r'deezer\.com(?:\/[a-z]{2})?\/album\/(\d+)',
                'playlist': r'deezer\.com(?:\/[a-z]{2})?\/playlist\/(\d+)'
            }
            
            for content_type, pattern in patterns.items():
                match = re.search(pattern, url)
                if match:
                    deezer_id = int(match.group(1))
                    logger.info(f"Extracted {content_type} with ID: {deezer_id}")
                    return content_type, deezer_id
                    
            logger.error(f"No matching pattern found for URL: {url}")
            return None, None
            
        except Exception as e:
            logger.error(f"Error extracting info from URL {url}: {str(e)}", exc_info=True)
            return None, None

    def get_deezer_info(self, content_type: str, deezer_id: int) -> Dict[str, Any]:
        """Get information from Deezer API"""
        try:
            logger.info(f"Fetching Deezer info - Type: {content_type}, ID: {deezer_id}")
            url = f"https://api.deezer.com/{content_type}/{deezer_id}"
            response = requests.get(url)
            
            if response.status_code == 200:
                logger.info(f"Successfully retrieved info for {content_type} {deezer_id}")
                return response.json()
            else:
                error_msg = f"Failed to get Deezer info: HTTP {response.status_code}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Error getting Deezer info for {content_type} {deezer_id}: {str(e)}", exc_info=True)
            raise

    async def create_zip(self, file_path: str, title: str) -> Optional[str]:
        """Create ZIP archive for album/playlist"""
        try:
            logger.info(f"Creating ZIP archive for: {title}")
            success, zip_path = self.file_handler.create_zip_archive([file_path], f"{title}.zip")
            
            if success:
                logger.info(f"Successfully created ZIP archive: {zip_path}")
                return zip_path
            else:
                logger.error(f"Failed to create ZIP archive for: {title}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating ZIP archive for {title}: {str(e)}", exc_info=True)
            return None
    
    async def get_track_list(self, content_type: str, deezer_id: int) -> list:
        """Get list of track IDs from album or playlist"""
        try:
            logger.info(f"Getting track list for {content_type} {deezer_id}")
            
            if content_type == 'track':
                logger.info(f"Single track requested: {deezer_id}")
                return [deezer_id]
            
            elif content_type in ['album', 'playlist']:
                info = self.get_deezer_info(content_type, deezer_id)
                track_ids = [track['id'] for track in info['tracks']['data']]
                logger.info(f"Retrieved {len(track_ids)} tracks from {content_type} {deezer_id}")
                return track_ids
            
            else:
                error_msg = f"Invalid content type: {content_type}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
        except Exception as e:
            logger.error(f"Error getting track list for {content_type} {deezer_id}: {str(e)}", exc_info=True)
            raise
