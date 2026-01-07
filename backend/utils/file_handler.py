"""Utility functions for the backend."""
import os
import shutil
import asyncio
import logging
import subprocess
from typing import List, Tuple, Optional, Any

# Configure logger
logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove invalid characters"""
    import re
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Remove control characters
    filename = "".join(ch for ch in filename if ord(ch) >= 32)
    return filename.strip()


class FileHandler:
    """Handle file operations for music downloads"""
    
    def __init__(self, temp_dir: str = 'temp'):
        """Initialize FileHandler with temporary directory path"""
        self.temp_dir = temp_dir
        self._ensure_temp_dir()
        logger.info(f"FileHandler initialized with temp directory: {temp_dir}")

    def _ensure_temp_dir(self):
        """Ensure temporary directory exists"""
        try:
            if not os.path.exists(self.temp_dir):
                os.makedirs(self.temp_dir)
                logger.debug(f"Created temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Failed to create temporary directory {self.temp_dir}: {str(e)}", exc_info=True)
            raise

    async def save_audio_file(self, file_data: bytes, filename: str) -> Tuple[bool, str]:
        """Save audio file to temporary directory"""
        try:
            safe_filename = sanitize_filename(filename)
            file_path = os.path.join(self.temp_dir, safe_filename)
            logger.debug(f"Saving audio file: {safe_filename}")
            
            # Write file asynchronously
            async def write_file():
                with open(file_path, 'wb') as f:
                    f.write(file_data)
            
            await asyncio.get_event_loop().run_in_executor(None, lambda: write_file())
            
            file_size = os.path.getsize(file_path)
            logger.info(f"Audio file saved successfully: {file_path} (Size: {file_size} bytes)")
            return True, file_path
            
        except Exception as e:
            logger.error(f"Failed to save audio file {filename}: {str(e)}", exc_info=True)
            return False, str(e)

    def create_zip_archive(self, files: List[str], archive_name: str) -> Tuple[bool, str]:
        """Create ZIP archive from list of files"""
        try:
            safe_archive_name = sanitize_filename(archive_name)
            archive_path = os.path.join(self.temp_dir, safe_archive_name)
            logger.info(f"Creating ZIP archive: {safe_archive_name} with {len(files)} files")
            
            # Create ZIP archive
            shutil.make_archive(
                archive_path.rsplit('.', 1)[0],  # Remove extension for make_archive
                'zip',
                self.temp_dir,
                files
            )
            
            zip_path = archive_path + '.zip'
            zip_size = os.path.getsize(zip_path)
            logger.info(f"ZIP archive created successfully: {zip_path} (Size: {zip_size} bytes)")
            return True, zip_path
            
        except Exception as e:
            logger.error(f"Failed to create ZIP archive {archive_name}: {str(e)}", exc_info=True)
            return False, str(e)

    def get_audio_duration(self, file_path: str) -> Optional[int]:
        """Get audio file duration using mutagen or ffprobe"""
        return get_audio_duration(file_path)

    def cleanup_temp_files(self, file_paths: List[str] = None):
        """Clean up temporary files"""
        try:
            if file_paths:
                logger.debug(f"Cleaning up {len(file_paths)} specific files")
                # Remove specific files
                for path in file_paths:
                    if os.path.exists(path):
                        os.remove(path)
                        logger.debug(f"Removed file: {path}")
                    else:
                        logger.warning(f"File not found for cleanup: {path}")
            else:
                logger.debug("Cleaning up entire temp directory")
                # Clean entire temp directory
                files_removed = 0
                for filename in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            files_removed += 1
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                            files_removed += 1
                    except Exception as e:
                        logger.error(f"Failed to remove {file_path}: {str(e)}", exc_info=True)
                logger.info(f"Cleanup completed: {files_removed} items removed")
            
        except Exception as e:
            logger.error(f"Failed to clean up temporary files: {str(e)}", exc_info=True)


def get_audio_duration(file_path: str) -> int:
    """
    Get the duration of an audio file in seconds.
    """
    try:
        # Try using mutagen for audio duration
        from mutagen import File
        audio = File(file_path)
        if audio and audio.info:
            return int(audio.info.length)
    except ImportError:
        logger.warning("mutagen not installed, trying ffprobe")
    except Exception as e:
        logger.warning(f"mutagen failed: {e}")
    
    try:
        # Fallback to ffprobe
        result = subprocess.run(
            [
                'ffprobe', '-v', 'error', '-show_entries', 
                'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return int(float(result.stdout.strip()))
    except Exception as e:
        logger.warning(f"ffprobe failed: {e}")
    
    return 0
