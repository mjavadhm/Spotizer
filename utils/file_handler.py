import os
import shutil
import asyncio
import ffmpeg
from typing import List, Tuple, Optional
from .url_validator import sanitize_filename
from logger import get_logger

logger = get_logger(__name__)

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
                logger.info(f"Created temporary directory: {self.temp_dir}")
            else:
                logger.info(f"Using existing temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Failed to create temporary directory {self.temp_dir}: {str(e)}", exc_info=True)
            raise

    async def save_audio_file(self, file_data: bytes, filename: str) -> Tuple[bool, str]:
        """Save audio file to temporary directory"""
        try:
            safe_filename = sanitize_filename(filename)
            file_path = os.path.join(self.temp_dir, safe_filename)
            logger.info(f"Saving audio file: {safe_filename}")
            
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
        """Get audio file duration using ffmpeg"""
        try:
            logger.info(f"Getting duration for audio file: {file_path}")
            probe = ffmpeg.probe(file_path)
            duration = float(probe['format']['duration'])
            logger.info(f"Audio duration: {duration} seconds")
            return int(duration)
            
        except Exception as e:
            logger.error(f"Failed to get audio duration for {file_path}: {str(e)}", exc_info=True)
            return None

    def create_m3u_playlist(self, tracks: List[Tuple[str, int, str]], playlist_name: str) -> Tuple[bool, str]:
        """Create M3U playlist file"""
        try:
            safe_playlist_name = sanitize_filename(playlist_name)
            if not safe_playlist_name.endswith('.m3u'):
                safe_playlist_name += '.m3u'
                
            playlist_path = os.path.join(self.temp_dir, safe_playlist_name)
            logger.info(f"Creating M3U playlist: {safe_playlist_name} with {len(tracks)} tracks")
            
            with open(playlist_path, 'w', encoding='utf-8') as f:
                f.write('#EXTM3U\n')
                for title, duration, filename in tracks:
                    f.write(f'#EXTINF:{duration},{title}\n')
                    f.write(f'{filename}\n')
            
            playlist_size = os.path.getsize(playlist_path)
            logger.info(f"M3U playlist created successfully: {playlist_path} (Size: {playlist_size} bytes)")
            return True, playlist_path
            
        except Exception as e:
            logger.error(f"Failed to create M3U playlist {playlist_name}: {str(e)}", exc_info=True)
            return False, str(e)

    def cleanup_temp_files(self, file_paths: List[str] = None):
        """Clean up temporary files"""
        try:
            if file_paths:
                logger.info(f"Cleaning up {len(file_paths)} specific files")
                # Remove specific files
                for path in file_paths:
                    if os.path.exists(path):
                        os.remove(path)
                        logger.info(f"Removed file: {path}")
                    else:
                        logger.warning(f"File not found for cleanup: {path}")
            else:
                logger.info("Cleaning up entire temp directory")
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
                        logger.info(f"Removed: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to remove {file_path}: {str(e)}", exc_info=True)
                logger.info(f"Cleanup completed: {files_removed} items removed")
            
        except Exception as e:
            logger.error(f"Failed to clean up temporary files: {str(e)}", exc_info=True)

    def ensure_audio_format(self, file_path: str, target_format: str) -> Tuple[bool, str]:
        """Ensure audio file is in the correct format"""
        try:
            logger.info(f"Checking audio format for: {file_path}")
            # Get current format
            probe = ffmpeg.probe(file_path)
            current_format = probe['format']['format_name']
            
            # If already in correct format, return original path
            if current_format.lower() == target_format.lower():
                logger.info(f"File already in target format {target_format}")
                return True, file_path
            
            # Convert to target format
            output_path = file_path.rsplit('.', 1)[0] + '.' + target_format.lower()
            logger.info(f"Converting from {current_format} to {target_format}")
            
            stream = ffmpeg.input(file_path)
            stream = ffmpeg.output(stream, output_path)
            ffmpeg.run(stream, overwrite_output=True)
            
            # Remove original file
            os.remove(file_path)
            
            output_size = os.path.getsize(output_path)
            logger.info(f"Audio converted successfully: {output_path} (Size: {output_size} bytes)")
            return True, output_path
            
        except Exception as e:
            logger.error(f"Failed to convert audio format for {file_path}: {str(e)}", exc_info=True)
            return False, str(e)

    def get_file_size(self, file_path: str) -> Optional[int]:
        """Get file size in bytes"""
        try:
            size = os.path.getsize(file_path)
            logger.info(f"File size for {file_path}: {size} bytes")
            return size
        except Exception as e:
            logger.error(f"Failed to get file size for {file_path}: {str(e)}", exc_info=True)
            return None

    def is_valid_audio_file(self, file_path: str) -> bool:
        """Check if file is a valid audio file"""
        try:
            logger.info(f"Validating audio file: {file_path}")
            probe = ffmpeg.probe(file_path)
            is_valid = 'audio' in probe['streams'][0]['codec_type']
            logger.info(f"Audio file validation result: {'valid' if is_valid else 'invalid'}")
            return is_valid
        except Exception as e:
            logger.error(f"Failed to validate audio file {file_path}: {str(e)}", exc_info=True)
            return False
    
    async def playlist_creator(self, musics: List[Tuple[str, int, str]], file_path: str):
        """Create a playlist file"""
        try:
            logger.info(f"Creating playlist file: {file_path} with {len(musics)} tracks")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for name, duration, path in musics:
                    f.write(f"#EXTINF:{duration},{name}\n")
                    f.write(f"{path}\n")
            
            playlist_size = os.path.getsize(file_path)
            logger.info(f"Playlist created successfully: {file_path} (Size: {playlist_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create playlist {file_path}: {str(e)}", exc_info=True)
            return False
