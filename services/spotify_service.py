import os
import logging
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class SpotifyService:
    def __init__(self):
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.sp = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
        )

    def convert_to_deezer_url(self, spotify_url: str) -> Optional[str]:
        """Convert Spotify URL to Deezer URL"""
        try:
            # Extract Spotify ID and type
            if 'track' in spotify_url:
                spotify_id = spotify_url.split('track/')[1].split('?')[0]
                track_info = self.sp.track(spotify_id)
                query = f"{track_info['name']} {track_info['artists'][0]['name']}"
                deezer_url = self.search_on_deezer('track', query)
                if not deezer_url:
                    logger.error(f"Could not find Deezer equivalent for Spotify track: {query}")
                return deezer_url
            elif 'album' in spotify_url:
                spotify_id = spotify_url.split('album/')[1].split('?')[0]
                album_info = self.sp.album(spotify_id)
                query = f"{album_info['name']} {album_info['artists'][0]['name']}"
                deezer_url = self.search_on_deezer('album', query)
                if not deezer_url:
                    logger.error(f"Could not find Deezer equivalent for Spotify album: {query}")
                return deezer_url
            logger.error(f"Unsupported Spotify URL format: {spotify_url}")
            return None
        except Exception as e:
            logger.error(f"Error converting Spotify URL: {str(e)}")
            return None

    def search_on_deezer(self, content_type: str, query: str) -> Optional[str]:
        """Search for content on Deezer"""
        try:
            response = requests.get(
                'https://api.deezer.com/search',
                params={'q': query, 'type': content_type}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('total', 0) > 0 and data.get('data'):
                    item = data['data'][0]
                    if 'id' in item:
                        return f"https://www.deezer.com/{content_type}/{item['id']}"
            logger.error(f"No results found on Deezer for query: {query}")
            return None
        except Exception as e:
            logger.error(f"Error searching Deezer: {str(e)}")
            return None

    async def search(self, query: str, search_type: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Search on Spotify"""
        try:
            results = self.sp.search(
                q=query,
                type=search_type,
                limit=limit,
                offset=offset
            )
            return results[f"{search_type}s"]['items']
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []

    async def get_item_info(self, item_type: str, item_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a Spotify item"""
        try:
            if item_type == 'track':
                return self.sp.track(item_id)
            elif item_type == 'album':
                return self.sp.album(item_id)
            elif item_type == 'playlist':
                return self.sp.playlist(item_id)
            return None
        except Exception as e:
            logger.error(f"Error getting item info: {str(e)}")
            return None
