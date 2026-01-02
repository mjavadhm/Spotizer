import os
import re
import logging
import requests
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass

from ..config import settings

logger = logging.getLogger(__name__)

# Lazy initialization of deezer downloader
_deedownload = None


def get_deedownload():
    """Get or initialize the Deezer downloader"""
    global _deedownload
    if _deedownload is None:
        try:
            from deezloader.deezloader import DeeLogin
            arl = settings.DEEZER_ARL
            if arl:
                _deedownload = DeeLogin(arl=arl)
                logger.info("DeezerService: DeeLogin initialized")
            else:
                logger.warning("DeezerService: No ARL token provided")
        except ImportError:
            logger.warning("DeezerService: deezloader not installed")
        except Exception as e:
            logger.error(f"DeezerService: Failed to initialize DeeLogin: {e}")
    return _deedownload


@dataclass
class DownloadResult:
    success: bool
    track_info: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    error: Optional[str] = None


class DeezerService:
    def __init__(self):
        logger.info("DeezerService initialized")

    def extract_info_from_url(self, url: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract content type and ID from Deezer URL"""
        try:
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
            logger.error(f"Error extracting info from URL {url}: {str(e)}")
            return None, None

    def get_deezer_info(self, content_type: str, deezer_id: int) -> Dict[str, Any]:
        """Get information from Deezer API"""
        try:
            url = f"https://api.deezer.com/{content_type}/{deezer_id}"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to get Deezer info: HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"Error getting Deezer info: {str(e)}")
            raise

    async def get_track_info(self, track_id: int) -> Optional[Dict[str, Any]]:
        """Get track information from Deezer"""
        try:
            info = self.get_deezer_info('track', track_id)
            return {
                'id': info['id'],
                'title': info['title'],
                'artist': info['artist']['name'],
                'album': info['album']['title'],
                'duration': info['duration'],
                'preview': info.get('preview'),
                'cover': info['album'].get('cover_medium')
            }
        except Exception as e:
            logger.error(f"Error getting track info: {str(e)}")
            return None

    async def get_album_info(self, album_id: int) -> Optional[Dict[str, Any]]:
        """Get album information from Deezer"""
        try:
            info = self.get_deezer_info('album', album_id)
            return {
                'id': info['id'],
                'title': info['title'],
                'artist': info['artist']['name'],
                'cover': info.get('cover_medium'),
                'nb_tracks': info['nb_tracks'],
                'release_date': info.get('release_date'),
                'tracks': [
                    {
                        'id': track['id'],
                        'title': track['title'],
                        'duration': track['duration']
                    }
                    for track in info.get('tracks', {}).get('data', [])
                ]
            }
        except Exception as e:
            logger.error(f"Error getting album info: {str(e)}")
            return None

    async def get_playlist_info(self, playlist_id: int) -> Optional[Dict[str, Any]]:
        """Get playlist information from Deezer"""
        try:
            info = self.get_deezer_info('playlist', playlist_id)
            return {
                'id': info['id'],
                'title': info['title'],
                'creator': info['creator']['name'],
                'picture': info.get('picture_medium'),
                'nb_tracks': info['nb_tracks'],
                'tracks': [
                    {
                        'id': track['id'],
                        'title': track['title'],
                        'artist': track['artist']['name'],
                        'duration': track['duration']
                    }
                    for track in info.get('tracks', {}).get('data', [])
                ]
            }
        except Exception as e:
            logger.error(f"Error getting playlist info: {str(e)}")
            return None

    async def get_track_list(self, content_type: str, deezer_id: int) -> List[int]:
        """Get list of track IDs from album or playlist"""
        try:
            if content_type == 'track':
                return [deezer_id]

            elif content_type in ['album', 'playlist']:
                info = self.get_deezer_info(content_type, deezer_id)
                if "tracks" in info:
                    track_ids = [track['id'] for track in info['tracks']['data']]
                    logger.info(f"Retrieved {len(track_ids)} tracks from {content_type}")
                    return track_ids
                else:
                    raise ValueError(f"Error in getting track list: {content_type} {deezer_id}")
            else:
                raise ValueError(f"Invalid content type: {content_type}")

        except Exception as e:
            logger.error(f"Error getting track list: {str(e)}")
            raise

    def convert_spotify_to_deezer(self, spotify_url: str) -> Optional[str]:
        """Convert Spotify URL to Deezer URL"""
        try:
            deedownload = get_deedownload()
            if not deedownload:
                logger.error("DeeLogin not available")
                return None

            if 'track' in spotify_url:
                return deedownload.convert_spoty_to_dee_link_track(spotify_url)
            elif 'album' in spotify_url:
                return deedownload.convert_spoty_to_dee_link_album(spotify_url)
            else:
                logger.error(f"Unsupported Spotify URL type: {spotify_url}")
                return None

        except Exception as e:
            logger.error(f"Error converting Spotify URL: {str(e)}")
            return None

    async def download(
        self,
        url: str,
        output_folder: str = "downloads",
        quality: str = "MP3_320",
        make_zip: bool = False
    ):
        """Download track/album/playlist from Deezer"""
        try:
            deedownload = get_deedownload()
            if not deedownload:
                return DownloadResult(success=False, error="DeeLogin not available")

            content_type, deezer_id = self.extract_info_from_url(url)
            if not content_type or not deezer_id:
                return DownloadResult(success=False, error="Invalid Deezer URL")

            logger.info(f"Downloading {content_type} with ID: {deezer_id}")
            smart = deedownload.download_smart(
                url,
                output_folder,
                quality_download=quality,
                make_zip=make_zip
            )
            logger.info(f"Successfully downloaded {content_type}")
            return smart

        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            return DownloadResult(success=False, error=str(e))

    def search_deezer(self, query: str, search_type: str = "track") -> List[Dict[str, Any]]:
        """Search on Deezer"""
        try:
            response = requests.get(
                f"https://api.deezer.com/search/{search_type}",
                params={'q': query}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            return []
        except Exception as e:
            logger.error(f"Error searching Deezer: {str(e)}")
            return []


# Singleton instance
_deezer_service: Optional[DeezerService] = None


def get_deezer_service() -> DeezerService:
    global _deezer_service
    if _deezer_service is None:
        _deezer_service = DeezerService()
    return _deezer_service
