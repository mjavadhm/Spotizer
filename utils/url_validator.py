import re
import os
import validators
from typing import Tuple, Dict, Any


class URLValidator:
    """URL validation utilities"""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate if string is a valid URL"""
        return validators.url(url) is True

    @staticmethod
    def is_deezer_url(url: str) -> bool:
        """Check if URL is a valid Deezer URL"""
        patterns = {
            'track': r'deezer\.com(?:\/[a-z]{2})?\/track\/(\d+)',
            'album': r'deezer\.com(?:\/[a-z]{2})?\/album\/(\d+)',
            'playlist': r'deezer\.com(?:\/[a-z]{2})?\/playlist\/(\d+)'
        }
        
        return any(re.search(pattern, url) for pattern in patterns.values())

    @staticmethod
    def is_spotify_url(url: str) -> bool:
        """Check if URL is a valid Spotify URL"""
        patterns = {
            'track': r'open\.spotify\.com\/track\/([a-zA-Z0-9]+)',
            'album': r'open\.spotify\.com\/album\/([a-zA-Z0-9]+)',
            'playlist': r'open\.spotify\.com\/playlist\/([a-zA-Z0-9]+)',
            'artist': r'open\.spotify\.com\/artist\/([a-zA-Z0-9]+)'
        }
        
        return any(re.search(pattern, url) for pattern in patterns.values())

    @staticmethod
    def extract_deezer_info(url: str) -> Tuple[str, int]:
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

    @staticmethod
    def extract_spotify_info(url: str) -> Tuple[str, str]:
        """Extract content type and ID from Spotify URL"""
        patterns = {
            'track': r'open\.spotify\.com\/track\/([a-zA-Z0-9]+)',
            'album': r'open\.spotify\.com\/album\/([a-zA-Z0-9]+)',
            'playlist': r'open\.spotify\.com\/playlist\/([a-zA-Z0-9]+)',
            'artist': r'open\.spotify\.com\/artist\/([a-zA-Z0-9]+)'
        }
        
        for content_type, pattern in patterns.items():
            match = re.search(pattern, url)
            if match:
                return content_type, match.group(1)
        
        return None, None

def validate_settings(settings: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate user settings"""
    valid_qualities = ['MP3_128', 'MP3_320', 'FLAC']
    valid_languages = ['en', 'fa']  # Add more supported languages as needed
    
    if 'download_quality' in settings:
        quality = settings['download_quality']
        if quality not in valid_qualities:
            return False, f"Invalid quality setting. Must be one of: {', '.join(valid_qualities)}"
    
    if 'make_zip' in settings:
        if not isinstance(settings['make_zip'], bool):
            return False, "make_zip setting must be a boolean value"
    
    if 'language' in settings:
        language = settings['language']
        if language not in valid_languages:
            return False, f"Invalid language setting. Must be one of: {', '.join(valid_languages)}"
    
    return True, "Settings are valid"

def validate_download_request(content_type: str, quality: str) -> Tuple[bool, str]:
    """Validate download request parameters"""
    valid_content_types = ['track', 'album', 'playlist']
    valid_qualities = ['MP3_128', 'MP3_320', 'FLAC']
    
    if content_type not in valid_content_types:
        return False, f"Invalid content type. Must be one of: {', '.join(valid_content_types)}"
    
    if quality not in valid_qualities:
        return False, f"Invalid quality setting. Must be one of: {', '.join(valid_qualities)}"
    
    return True, "Download request is valid"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to be safe for file system"""
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
    # Limit length while preserving extension
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length-len(ext)] + ext
    return filename
