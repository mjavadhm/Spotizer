import os
import re
import requests
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, List, Union

from deezloader.deezloader import DeeLogin
from deezloader.models.smart import Smart

from utils.file_handler import FileHandler
from logger import get_logger

logger = get_logger(__name__)

@dataclass
class DownloadResult:
    success: bool
    track_info: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    error: Optional[str] = None

class DeezerService:
    def __init__(self):
        self.file_handler = FileHandler()
        self.client: Optional[DeeLogin] = None
        self._initialize_client()
        logger.info("DeezerService initialized")

    def _initialize_client(self):
        """Initialize the Deezer client with ARL from environment."""
        arl = os.getenv('DEEZER_ARL')
        if not arl:
            logger.error("DEEZER_ARL environment variable is not set.")
            return

        try:
            self.client = DeeLogin(arl=arl)
            logger.info("Deezer client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Deezer client: {str(e)}", exc_info=True)

    async def download(self, url: str, output_folder="downloads", quality_download: str = 'MP3_320', make_zip: bool = False) -> Union[Smart, DownloadResult, bool]:
        """Download track/album/playlist from Deezer"""
        import asyncio
        
        if not self.client:
            logger.error("Deezer client is not initialized. Cannot download.")
            return DownloadResult(False, error="Deezer client not initialized")

        try:
            logger.info(f"Starting download - URL: {url}, Quality: {quality_download}, Make ZIP: {make_zip}")
            content_type, deezer_id = self.extract_info_from_url(url)
            
            if not content_type or not deezer_id:
                logger.error(f"Invalid Deezer URL provided: {url}")
                return DownloadResult(False, error="Invalid Deezer URL")

            logger.info(f"Downloading {content_type} with ID: {deezer_id}")
            loop = asyncio.get_event_loop()
            
            # Run blocking deezloader call in thread pool with timeout
            try:
                smart = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self.client.download_smart(url, output_folder, quality_download=quality_download, make_zip=make_zip)
                    ),
                    timeout=300.0  # 5 minute timeout for downloads
                )
                logger.info(f"Successfully downloaded {content_type} - ID: {deezer_id}")
                return smart
            except asyncio.TimeoutError:
                logger.error(f"Timeout downloading {content_type} {deezer_id}")
                return DownloadResult(False, error="Download timed out")

        except Exception as e:
            logger.error(f"Download error for URL {url}: {str(e)}", exc_info=True)
            return False

    def extract_info_from_url(self, url: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract content type and ID from Deezer URL"""
        try:
            # logger.info(f"Extracting info from URL: {url}")
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

    async def get_deezer_info(self, content_type: str, deezer_id: int) -> Dict[str, Any]:
        """Get information from Deezer API"""
        import asyncio
        
        def _fetch():
            url = f"https://api.deezer.com/{content_type}/{deezer_id}"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"Failed to get Deezer info: HTTP {response.status_code}"
                logger.error(error_msg)
                raise Exception(error_msg)
        
        try:
            return await asyncio.to_thread(_fetch)
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
    
    async def get_track_list(self, content_type: str, deezer_id: int) -> List[int]:
        """Get list of track IDs from album or playlist"""
        try:
            logger.info(f"Getting track list for {content_type} {deezer_id}")
            
            if content_type == 'track':
                logger.info(f"Single track requested: {deezer_id}")
                return [deezer_id]
            
            elif content_type in ['album', 'playlist']:
                info = await self.get_deezer_info(content_type, deezer_id)
                if "tracks" in info:
                    track_ids = [track['id'] for track in info['tracks']['data']]
                    logger.info(f"Retrieved {len(track_ids)} tracks from {content_type} {deezer_id}")
                    return track_ids
                else:
                    error_msg = f"Error in getting track list: {content_type} {deezer_id}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            else:
                error_msg = f"Invalid content type: {content_type}"
                logger.error(error_msg)
                raise ValueError(error_msg)
                
        except Exception as e:
            logger.error(f"Error getting track list for {content_type} {deezer_id}: {str(e)}", exc_info=True)
            raise
    
    async def convert_to_deezer(self, url: str) -> Optional[str]:
        """Convert Spotify URL to Deezer URL"""
        import asyncio
        
        print(f"[DEBUG] convert_to_deezer: ENTER - url={url}")
        
        if not self.client:
            print(f"[DEBUG] convert_to_deezer: client is None!")
            logger.error("Deezer client is not initialized. Cannot convert URL.")
            return None

        try:
            loop = asyncio.get_event_loop()
            print(f"[DEBUG] convert_to_deezer: got event loop")
            
            if 'track' in url:
                print(f"[DEBUG] convert_to_deezer: detected TRACK url")
                logger.info(f"Starting Spotify to Deezer conversion for track: {url}")
                # Run blocking call in executor with timeout
                try:
                    print(f"[DEBUG] convert_to_deezer: calling run_in_executor...")
                    result = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            self.client.convert_spoty_to_dee_link_track, 
                            url
                        ),
                        timeout=30.0  # 30 second timeout
                    )
                    print(f"[DEBUG] convert_to_deezer: executor returned - result={result}")
                    logger.info(f"Conversion completed: {result}")
                    return result
                except asyncio.TimeoutError:
                    print(f"[DEBUG] convert_to_deezer: TIMEOUT!")
                    logger.error(f"Timeout converting track URL: {url}")
                    return None
            elif 'album' in url:
                print(f"[DEBUG] convert_to_deezer: detected ALBUM url")
                logger.info(f"Starting Spotify to Deezer conversion for album: {url}")
                try:
                    print(f"[DEBUG] convert_to_deezer: calling run_in_executor...")
                    result = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            self.client.convert_spoty_to_dee_link_album, 
                            url
                        ),
                        timeout=30.0
                    )
                    print(f"[DEBUG] convert_to_deezer: executor returned - result={result}")
                    logger.info(f"Conversion completed: {result}")
                    return result
                except asyncio.TimeoutError:
                    print(f"[DEBUG] convert_to_deezer: TIMEOUT!")
                    logger.error(f"Timeout converting album URL: {url}")
                    return None
            print(f"[DEBUG] convert_to_deezer: returning url as-is")
            return url
        except Exception as e:
            print(f"[DEBUG] convert_to_deezer: EXCEPTION - {e}")
            logger.error(f"Error converting {url}: {str(e)}", exc_info=True)
            raise
