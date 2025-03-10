import re
import os
import validators
from typing import Tuple, Dict, Any
from logger import get_logger

logger = get_logger(__name__)

class URLValidator:
    """URL validation utilities"""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate if string is a valid URL"""
        try:
            is_valid = validators.url(url) is True
            if is_valid:
                logger.info(f"Valid URL format: {url}")
            else:
                logger.warning(f"Invalid URL format: {url}")
            return is_valid
        except Exception as e:
            logger.error(f"Error validating URL {url}: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def is_deezer_url(url: str) -> bool:
        """Check if URL is a valid Deezer URL"""
        try:
            patterns = {
                'track': r'deezer\.com(?:\/[a-z]{2})?\/track\/(\d+)',
                'album': r'deezer\.com(?:\/[a-z]{2})?\/album\/(\d+)',
                'playlist': r'deezer\.com(?:\/[a-z]{2})?\/playlist\/(\d+)'
            }
            
            for content_type, pattern in patterns.items():
                if re.search(pattern, url):
                    logger.info(f"Valid Deezer {content_type} URL: {url}")
                    return True
                    
            logger.warning(f"Invalid Deezer URL format: {url}")
            return False
            
        except Exception as e:
            logger.error(f"Error validating Deezer URL {url}: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def is_spotify_url(url: str) -> bool:
        """Check if URL is a valid Spotify URL"""
        try:
            patterns = {
                'track': r'open\.spotify\.com\/track\/([a-zA-Z0-9]+)',
                'album': r'open\.spotify\.com\/album\/([a-zA-Z0-9]+)',
                'playlist': r'open\.spotify\.com\/playlist\/([a-zA-Z0-9]+)',
                'artist': r'open\.spotify\.com\/artist\/([a-zA-Z0-9]+)'
            }
            
            for content_type, pattern in patterns.items():
                if re.search(pattern, url):
                    logger.info(f"Valid Spotify {content_type} URL: {url}")
                    return True
                    
            logger.warning(f"Invalid Spotify URL format: {url}")
            return False
            
        except Exception as e:
            logger.error(f"Error validating Spotify URL {url}: {str(e)}", exc_info=True)
            return False

    @staticmethod
    def extract_deezer_info(url: str) -> Tuple[str, int]:
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
                    logger.info(f"Extracted Deezer info - Type: {content_type}, ID: {deezer_id}")
                    return content_type, deezer_id
            
            logger.warning(f"Could not extract Deezer info from URL: {url}")
            return None, None
            
        except Exception as e:
            logger.error(f"Error extracting Deezer info from URL {url}: {str(e)}", exc_info=True)
            return None, None

    @staticmethod
    def extract_spotify_info(url: str) -> Tuple[str, str]:
        """Extract content type and ID from Spotify URL"""
        try:
            patterns = {
                'track': r'open\.spotify\.com\/track\/([a-zA-Z0-9]+)',
                'album': r'open\.spotify\.com\/album\/([a-zA-Z0-9]+)',
                'playlist': r'open\.spotify\.com\/playlist\/([a-zA-Z0-9]+)',
                'artist': r'open\.spotify\.com\/artist\/([a-zA-Z0-9]+)'
            }
            
            for content_type, pattern in patterns.items():
                match = re.search(pattern, url)
                if match:
                    spotify_id = match.group(1)
                    logger.info(f"Extracted Spotify info - Type: {content_type}, ID: {spotify_id}")
                    return content_type, spotify_id
            
            logger.warning(f"Could not extract Spotify info from URL: {url}")
            return None, None
            
        except Exception as e:
            logger.error(f"Error extracting Spotify info from URL {url}: {str(e)}", exc_info=True)
            return None, None

def validate_settings(settings: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate user settings"""
    try:
        logger.info(f"Validating settings: {settings}")
        valid_qualities = ['MP3_128', 'MP3_320', 'FLAC']
        valid_languages = ['en', 'fa']  # Add more supported languages as needed
        
        if 'download_quality' in settings:
            quality = settings['download_quality']
            if quality not in valid_qualities:
                error_msg = f"Invalid quality setting. Must be one of: {', '.join(valid_qualities)}"
                logger.warning(f"Settings validation failed: {error_msg}")
                return False, error_msg
        
        if 'make_zip' in settings:
            if not isinstance(settings['make_zip'], bool):
                error_msg = "make_zip setting must be a boolean value"
                logger.warning(f"Settings validation failed: {error_msg}")
                return False, error_msg
        
        if 'language' in settings:
            language = settings['language']
            if language not in valid_languages:
                error_msg = f"Invalid language setting. Must be one of: {', '.join(valid_languages)}"
                logger.warning(f"Settings validation failed: {error_msg}")
                return False, error_msg
        
        logger.info("Settings validation successful")
        return True, "Settings are valid"
        
    except Exception as e:
        logger.error(f"Error validating settings: {str(e)}", exc_info=True)
        return False, f"Error validating settings: {str(e)}"

def validate_download_request(content_type: str, quality: str) -> Tuple[bool, str]:
    """Validate download request parameters"""
    try:
        logger.info(f"Validating download request - Content Type: {content_type}, Quality: {quality}")
        valid_content_types = ['track', 'album', 'playlist']
        valid_qualities = ['MP3_128', 'MP3_320', 'FLAC']
        
        if content_type not in valid_content_types:
            error_msg = f"Invalid content type. Must be one of: {', '.join(valid_content_types)}"
            logger.warning(f"Download request validation failed: {error_msg}")
            return False, error_msg
        
        if quality not in valid_qualities:
            error_msg = f"Invalid quality setting. Must be one of: {', '.join(valid_qualities)}"
            logger.warning(f"Download request validation failed: {error_msg}")
            return False, error_msg
        
        logger.info("Download request validation successful")
        return True, "Download request is valid"
        
    except Exception as e:
        logger.error(f"Error validating download request: {str(e)}", exc_info=True)
        return False, f"Error validating download request: {str(e)}"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to be safe for file system"""
    try:
        logger.info(f"Sanitizing filename: {filename}")
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Replace problematic characters with underscores
        filename = re.sub(r'[\s\(\)\[\]\{\}]+', '_', filename)
        # Remove consecutive underscores
        filename = re.sub(r'_+', '_', filename)
        # Remove leading/trailing underscores
        filename = filename.strip('_')
        # Ensure filename is not empty
        if not filename:
            filename = "untitled"
            logger.warning("Empty filename replaced with 'untitled'")
        # Limit length while preserving extension
        max_length = 255
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length-len(ext)] + ext
            logger.warning(f"Filename truncated to {max_length} characters")
        
        logger.info(f"Sanitized filename: {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"Error sanitizing filename {filename}: {str(e)}", exc_info=True)
        return "untitled"
