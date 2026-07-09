import os
import re
import asyncio
import subprocess
import glob
import aiohttp
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, Any, List

from tinytag import TinyTag
from logger import get_logger

logger = get_logger(__name__)

@dataclass
class DeemixTrackResult:
    file_path: str
    title: str = "Unknown Title"
    artist: str = "Unknown Artist"
    album: str = "Unknown Album"
    duration: Optional[int] = None

class DeezerAPIClient:
    BASE_URL = "https://api.deezer.com"

    @classmethod
    async def _request(cls, endpoint: str, params: dict = None):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{cls.BASE_URL}/{endpoint}", params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return None
        except Exception as e:
            logger.error(f"Deezer API request failed: {str(e)}")
            return None

    @classmethod
    def _format_duration(cls, seconds: int) -> str:
        if not seconds:
            return "0:00"
        m, s = divmod(seconds, 60)
        return f"{m}:{s:02d}"

    @classmethod
    async def search(cls, query: str, search_type: str, limit: int = 5, offset: int = 0) -> List[Dict]:
        """Search Deezer API and map to expected view format"""
        # Map search_type for deezer API
        endpoint = f"search/{search_type}"
        data = await cls._request(endpoint, {"q": query, "limit": limit, "index": offset})
        if not data or 'data' not in data:
            return []
            
        results = []
        for item in data['data']:
            if search_type == "track":
                results.append({
                    'id': str(item['id']),
                    'name': item['title'],
                    'artists': [{'id': str(item['artist']['id']), 'name': item['artist']['name']}],
                    'main_artist': item['artist']['name'],
                    'album': {'id': str(item['album']['id']), 'name': item['album']['title']},
                    'duration': cls._format_duration(item.get('duration', 0))
                })
            elif search_type == "album":
                results.append({
                    'id': str(item['id']),
                    'name': item['title'],
                    'main_artist': item['artist']['name']
                })
            elif search_type == "artist":
                results.append({
                    'id': str(item['id']),
                    'name': item['name']
                })
            elif search_type == "playlist":
                results.append({
                    'id': str(item['id']),
                    'name': item['title'],
                    'total_tracks': item.get('nb_tracks', 0)
                })
        return results

    @classmethod
    async def get_item_info(cls, content_type: str, item_id: str) -> Optional[Dict]:
        """Get full details of a specific item"""
        item = await cls._request(f"{content_type}/{item_id}")
        if not item or 'error' in item:
            return None
            
        if content_type == "track":
            # Attempt to get album info if present
            album_info = item.get('album', {})
            return {
                'id': str(item['id']),
                'name': item['title'],
                'url': item.get('link', f"https://www.deezer.com/track/{item['id']}"),
                'artists': [{'id': str(item['artist']['id']), 'name': item['artist']['name']}],
                'main_artist': item['artist']['name'],
                'album': {
                    'id': str(album_info.get('id', '')), 
                    'name': album_info.get('title', 'Unknown'),
                    'release_date': album_info.get('release_date', 'Unknown')
                },
                'duration': cls._format_duration(item.get('duration', 0)),
                'popularity': 0, # Deezer doesn't provide popularity directly
                'explicit': item.get('explicit_lyrics', False),
                'image': album_info.get('cover_xl') or album_info.get('cover_medium') or album_info.get('cover') or "https://e7.pngegg.com/pngimages/708/311/png-clipart-icon-logo-twitter-logo-twitter-logo-blue-social-media-thumbnail.png"
            }
        elif content_type == "album":
            tracks_data = await cls._request(f"album/{item_id}/tracks")
            tracks = []
            if tracks_data and 'data' in tracks_data:
                for t in tracks_data['data']:
                    tracks.append({
                        'id': str(t['id']),
                        'name': t['title'],
                        'duration': cls._format_duration(t.get('duration', 0)),
                        'artists': [{'id': str(t['artist']['id']), 'name': t['artist']['name']}],
                        'artist': t['artist']['name'],
                        'main_artist': t['artist']['name']
                    })
                    
            return {
                'id': str(item['id']),
                'name': item['title'],
                'url': item.get('link', f"https://www.deezer.com/album/{item['id']}"),
                'artists': [{'id': str(item['artist']['id']), 'name': item['artist']['name']}],
                'main_artist': item['artist']['name'],
                'release_date': item.get('release_date', 'Unknown'),
                'total_tracks': item.get('nb_tracks', 0),
                'image': item.get('cover_xl') or item.get('cover_medium') or item.get('cover') or "https://e7.pngegg.com/pngimages/708/311/png-clipart-icon-logo-twitter-logo-twitter-logo-blue-social-media-thumbnail.png",
                'tracks': tracks
            }
        elif content_type == "playlist":
            tracks_data = await cls._request(f"playlist/{item_id}/tracks")
            tracks = []
            if tracks_data and 'data' in tracks_data:
                for t in tracks_data['data']:
                    tracks.append({
                        'id': str(t['id']),
                        'name': t['title'],
                        'duration': cls._format_duration(t.get('duration', 0)),
                        'artists': [{'id': str(t['artist']['id']), 'name': t['artist']['name']}],
                        'artist': t['artist']['name'],
                        'main_artist': t['artist']['name']
                    })
                    
            return {
                'id': str(item['id']),
                'name': item['title'],
                'url': item.get('link', f"https://www.deezer.com/playlist/{item['id']}"),
                'description': item.get('description', ''),
                'total_tracks': item.get('nb_tracks', 0),
                'image': item.get('picture_xl') or item.get('picture_medium') or item.get('picture') or "https://e7.pngegg.com/pngimages/708/311/png-clipart-icon-logo-twitter-logo-twitter-logo-blue-social-media-thumbnail.png",
                'tracks': tracks
            }
        elif content_type == "artist":
            return {
                'id': str(item['id']),
                'name': item['name'],
                'url': item.get('link', f"https://www.deezer.com/artist/{item['id']}"),
                'followers': item.get('nb_fan', 0),
                'total_tracks': item.get('nb_album', 0),  # Not all endpoints return total tracks, nb_album is useful too, or fetch later
                'popularity': 0,
                'genres': [],
                'image': item.get('picture_xl') or item.get('picture_medium') or item.get('picture') or "https://e7.pngegg.com/pngimages/708/311/png-clipart-icon-logo-twitter-logo-twitter-logo-blue-social-media-thumbnail.png",
                'more_artist_info': {
                    'top_tracks': True,
                    'albums': True,
                    'related_artists': True
                }
            }
        return None

    @classmethod
    async def get_artist_top_tracks(cls, artist_id: str) -> List[Dict]:
        data = await cls._request(f"artist/{artist_id}/top")
        if not data or 'data' not in data:
            return []
        
        results = []
        for track in data['data']:
            results.append({
                'id': str(track['id']),
                'name': track['title'],
                'duration': cls._format_duration(track.get('duration', 0)),
                'artist': track['artist']['name'],
                'main_artist': track['artist']['name']
            })
        return results

    @classmethod
    async def get_artist_albums(cls, artist_id: str) -> List[Dict]:
        data = await cls._request(f"artist/{artist_id}/albums")
        if not data or 'data' not in data:
            return []
        
        # Fetch each album's detail in parallel to get nb_tracks
        async def fetch_album_detail(album):
            detail = await cls._request(f"album/{album['id']}")
            nb_tracks = detail.get('nb_tracks', 0) if detail else 0
            return {
                'id': str(album['id']),
                'name': album['title'],
                'release_date': album.get('release_date', 'Unknown'),
                'artist': album.get('artist', {}).get('name', 'Unknown'),
                'main_artist': album.get('artist', {}).get('name', 'Unknown'),
                'nb_tracks': nb_tracks
            }
        
        results = await asyncio.gather(*[fetch_album_detail(album) for album in data['data']])
        return list(results)

    @classmethod
    async def get_artist_related(cls, artist_id: str) -> List[Dict]:
        data = await cls._request(f"artist/{artist_id}/related")
        if not data or 'data' not in data:
            return []
            
        results = []
        for artist in data['data']:
            results.append({
                'id': str(artist['id']),
                'name': artist['name'],
                'artist': artist['name'],
                'main_artist': artist['name']
            })
        return results


@dataclass
class DeemixResult:
    success: bool
    tracks: List[DeemixTrackResult] = field(default_factory=list)
    error: Optional[str] = None
    is_album_or_playlist: bool = False

class DeezerService:
    def __init__(self):
        self.deemix_path = os.getenv('DEEMIX_PATH', 'tools/deemix/deemix')
        self.config_dir = os.path.abspath(os.getenv('DEEMIX_CONFIG_DIR', 'tools/deemix/config'))
        self.download_dir = os.path.abspath('downloads')
        self._setup_arl()
        logger.info("DeezerService initialized with CLI approach")

    def _setup_arl(self):
        """Write ARL token to deemix config"""
        arl = os.getenv('DEEZER_ARL')
        if not arl:
            logger.error("DEEZER_ARL environment variable is not set.")
            return

        os.makedirs(self.config_dir, exist_ok=True)
        arl_path = os.path.join(self.config_dir, '.arl')
        try:
            with open(arl_path, 'w') as f:
                f.write(arl)
            logger.info("ARL token configured for deemix")
        except Exception as e:
            logger.error(f"Failed to write ARL token: {str(e)}")

    def _map_quality(self, quality: str) -> str:
        """Map Spotizer quality to deemix bitrate flag"""
        mapping = {
            'MP3_128': '128',
            'MP3_320': '320',
            'FLAC': 'flac'
        }
        return mapping.get(quality, '320')

    def extract_info_from_url(self, url: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract content type and ID from Deezer URL"""
        try:
            patterns = {
                'track': r'deezer\.com(?:\/[a-z]{2})?\/track\/(\d+)',
                'album': r'deezer\.com(?:\/[a-z]{2})?\/album\/(\d+)',
                'playlist': r'deezer\.com(?:\/[a-z]{2})?\/playlist\/(\d+)',
                'artist': r'deezer\.com(?:\/[a-z]{2})?\/artist\/(\d+)'
            }
            
            for content_type, pattern in patterns.items():
                match = re.search(pattern, url)
                if match:
                    deezer_id = int(match.group(1))
                    return content_type, deezer_id
            return None, None
        except Exception as e:
            logger.error(f"Error extracting info from URL {url}: {str(e)}")
            return None, None

    async def download(self, url: str, output_folder="downloads", quality_download: str = 'MP3_320', make_zip: bool = False) -> DeemixResult:
        """Download track/album/playlist from Deezer using deemix-cli"""
        
        content_type, deezer_id = self.extract_info_from_url(url)
        if not content_type:
            return DeemixResult(False, error="Invalid Deezer URL")

        bitrate = self._map_quality(quality_download)
        
        # Determine specific download directory to isolate files for this download
        download_path = os.path.abspath(os.path.join(output_folder, f"deemix_{deezer_id}"))
        os.makedirs(download_path, exist_ok=True)
        
        # Run CLI in thread to avoid blocking asyncio loop
        def run_cli():
            cmd = [
                self.deemix_path, 
                url, 
                "-b", bitrate, 
                "-p", download_path
            ]
            env = os.environ.copy()
            env["DEEMIX_CONFIG_DIR"] = self.config_dir
            
            logger.info(f"Running deemix CLI: {' '.join(cmd)}")
            return subprocess.run(cmd, capture_output=True, text=True, env=env)

        try:
            logger.info(f"Starting download of {content_type} {deezer_id} (Quality: {bitrate})")
            process = await asyncio.to_thread(run_cli)
            
            logger.debug(f"deemix stdout: {process.stdout}")
            if process.stderr:
                logger.warning(f"deemix stderr: {process.stderr}")

            # Scan the download_path for audio files
            audio_files = []
            for ext in ('*.mp3', '*.flac', '*.m4a'):
                audio_files.extend(glob.glob(os.path.join(download_path, '**', ext), recursive=True))
            
            if not audio_files:
                return DeemixResult(False, error="No files were downloaded. Deemix failed.")
            
            tracks = []
            for file_path in audio_files:
                try:
                    tag = TinyTag.get(file_path)
                    tracks.append(DeemixTrackResult(
                        file_path=file_path,
                        title=tag.title or "Unknown Title",
                        artist=tag.artist or "Unknown Artist",
                        album=tag.album or "Unknown Album",
                        duration=int(tag.duration) if tag.duration else None
                    ))
                except Exception as e:
                    logger.error(f"Error parsing metadata for {file_path}: {str(e)}")
                    tracks.append(DeemixTrackResult(file_path=file_path))
            
            is_album_or_playlist = content_type in ['album', 'playlist', 'artist']
            
            return DeemixResult(
                success=True, 
                tracks=tracks, 
                is_album_or_playlist=is_album_or_playlist
            )
            
        except Exception as e:
            logger.error(f"Download error for URL {url}: {str(e)}", exc_info=True)
            return DeemixResult(False, error=str(e))
