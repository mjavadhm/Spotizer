import os
import re
import asyncio
import subprocess
import glob
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
                'playlist': r'deezer\.com(?:\/[a-z]{2})?\/playlist\/(\d+)'
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
            
            is_album_or_playlist = content_type in ['album', 'playlist']
            
            return DeemixResult(
                success=True, 
                tracks=tracks, 
                is_album_or_playlist=is_album_or_playlist
            )
            
        except Exception as e:
            logger.error(f"Download error for URL {url}: {str(e)}", exc_info=True)
            return DeemixResult(False, error=str(e))
