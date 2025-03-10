import os
import shutil
import logging
import asyncio
from typing import List, Tuple, Optional
import ffmpeg
from .url_validator import sanitize_filename

logger = logging.getLogger(__name__)

class FileHandler:
    """Handle file operations for music downloads"""
    
    def __init__(self, temp_dir: str = 'temp'):
        """Initialize FileHandler with temporary directory path"""
        self.temp_dir = temp_dir
        self._ensure_temp_dir()

    def _ensure_temp_dir(self):
        """Ensure temporary directory exists"""
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            logger.info(f"Created temporary directory: {self.temp_dir}")

    async def save_audio_file(self, file_data: bytes, filename: str) -> Tuple[bool, str]:
        """Save audio file to temporary directory"""
        try:
            safe_filename = sanitize_filename(filename)
            file_path = os.path.join(self.temp_dir, safe_filename)
            
            # Write file asynchronously
            async def write_file():
                with open(file_path, 'wb') as f:
                    f.write(file_data)
            
            await asyncio.get_event_loop().run_in_executor(None, lambda: write_file())
            
            logger.info(f"Audio file saved: {file_path}")
            return True, file_path
            
        except Exception as e:
            logger.error(f"Error saving audio file: {str(e)}")
            return False, str(e)

    def create_zip_archive(self, files: List[str], archive_name: str) -> Tuple[bool, str]:
        """Create ZIP archive from list of files"""
        try:
            safe_archive_name = sanitize_filename(archive_name)
            archive_path = os.path.join(self.temp_dir, safe_archive_name)
            
            # Create ZIP archive
            shutil.make_archive(
                archive_path.rsplit('.', 1)[0],  # Remove extension for make_archive
                'zip',
                self.temp_dir,
                files
            )
            
            zip_path = archive_path + '.zip'
            logger.info(f"ZIP archive created: {zip_path}")
            return True, zip_path
            
        except Exception as e:
            logger.error(f"Error creating ZIP archive: {str(e)}")
            return False, str(e)

    def get_audio_duration(self, file_path: str) -> Optional[int]:
        """Get audio file duration using ffmpeg"""
        try:
            probe = ffmpeg.probe(file_path)
            duration = float(probe['format']['duration'])
            return int(duration)
            
        except Exception as e:
            logger.error(f"Error getting audio duration: {str(e)}")
            return None

    def create_m3u_playlist(self, tracks: List[Tuple[str, int, str]], playlist_name: str) -> Tuple[bool, str]:
        """Create M3U playlist file"""
        try:
            safe_playlist_name = sanitize_filename(playlist_name)
            if not safe_playlist_name.endswith('.m3u'):
                safe_playlist_name += '.m3u'
                
            playlist_path = os.path.join(self.temp_dir, safe_playlist_name)
            
            with open(playlist_path, 'w', encoding='utf-8') as f:
                f.write('#EXTM3U\n')
                for title, duration, filename in tracks:
                    f.write(f'#EXTINF:{duration},{title}\n')
                    f.write(f'{filename}\n')
            
            logger.info(f"M3U playlist created: {playlist_path}")
            return True, playlist_path
            
        except Exception as e:
            logger.error(f"Error creating M3U playlist: {str(e)}")
            return False, str(e)

    def cleanup_temp_files(self, file_paths: List[str] = None):
        """Clean up temporary files"""
        try:
            if file_paths:
                # Remove specific files
                for path in file_paths:
                    if os.path.exists(path):
                        os.remove(path)
                        logger.info(f"Removed file: {path}")
            else:
                # Clean entire temp directory
                for filename in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                        logger.info(f"Removed: {file_path}")
                    except Exception as e:
                        logger.error(f"Error removing {file_path}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")

    def ensure_audio_format(self, file_path: str, target_format: str) -> Tuple[bool, str]:
        """Ensure audio file is in the correct format"""
        try:
            # Get current format
            probe = ffmpeg.probe(file_path)
            current_format = probe['format']['format_name']
            
            # If already in correct format, return original path
            if current_format.lower() == target_format.lower():
                return True, file_path
            
            # Convert to target format
            output_path = file_path.rsplit('.', 1)[0] + '.' + target_format.lower()
            
            stream = ffmpeg.input(file_path)
            stream = ffmpeg.output(stream, output_path)
            ffmpeg.run(stream, overwrite_output=True)
            
            # Remove original file
            os.remove(file_path)
            
            logger.info(f"Converted audio to {target_format}: {output_path}")
            return True, output_path
            
        except Exception as e:
            logger.error(f"Error converting audio format: {str(e)}")
            return False, str(e)

    def get_file_size(self, file_path: str) -> Optional[int]:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Error getting file size: {str(e)}")
            return None

    def is_valid_audio_file(self, file_path: str) -> bool:
        """Check if file is a valid audio file"""
        try:
            probe = ffmpeg.probe(file_path)
            return 'audio' in probe['streams'][0]['codec_type']
        except Exception:
            return False
    
    def playlist_creator(musics,file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for name, duration ,path in musics:
                f.write(f"#EXTINF:{duration},{name}\n")
                f.write(f"{path}\n")
