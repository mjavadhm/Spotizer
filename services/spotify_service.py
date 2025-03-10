import os
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import Optional, Dict, Any, List
from logger import get_logger

logger = get_logger(__name__)

class SpotifyService:
    def __init__(self):
        try:
            self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
            self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
            
            if not self.client_id or not self.client_secret:
                logger.error("Spotify credentials not found in environment variables")
                raise ValueError("Missing Spotify credentials")
                
            self.sp = spotipy.Spotify(
                auth_manager=SpotifyClientCredentials(
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
            )
            logger.info("SpotifyService initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SpotifyService: {str(e)}", exc_info=True)
            raise

    def convert_to_deezer_url(self, spotify_url: str) -> Optional[str]:
        """Convert Spotify URL to Deezer URL"""
        try:
            logger.info(f"Converting Spotify URL to Deezer URL: {spotify_url}")
            
            # Extract Spotify ID and type
            if 'track' in spotify_url:
                spotify_id = spotify_url.split('track/')[1].split('?')[0]
                logger.info(f"Extracted Spotify track ID: {spotify_id}")
                
                track_info = self.sp.track(spotify_id)
                query = f"{track_info['name']} {track_info['artists'][0]['name']}"
                logger.info(f"Searching Deezer for track: {query}")
                
                deezer_url = self.search_on_deezer('track', query)
                if not deezer_url:
                    logger.error(f"No Deezer equivalent found for Spotify track: {query}")
                    return None
                    
                logger.info(f"Found Deezer equivalent: {deezer_url}")
                return deezer_url
                
            elif 'album' in spotify_url:
                spotify_id = spotify_url.split('album/')[1].split('?')[0]
                logger.info(f"Extracted Spotify album ID: {spotify_id}")
                
                album_info = self.sp.album(spotify_id)
                query = f"{album_info['name']} {album_info['artists'][0]['name']}"
                logger.info(f"Searching Deezer for album: {query}")
                
                deezer_url = self.search_on_deezer('album', query)
                if not deezer_url:
                    logger.error(f"No Deezer equivalent found for Spotify album: {query}")
                    return None
                    
                logger.info(f"Found Deezer equivalent: {deezer_url}")
                return deezer_url
                
            logger.error(f"Unsupported Spotify URL format: {spotify_url}")
            return None
            
        except Exception as e:
            logger.error(f"Error converting Spotify URL {spotify_url}: {str(e)}", exc_info=True)
            return None

    def search_on_deezer(self, content_type: str, query: str) -> Optional[str]:
        """Search for content on Deezer"""
        try:
            logger.info(f"Searching Deezer - Type: {content_type}, Query: {query}")
            
            response = requests.get(
                'https://api.deezer.com/search',
                params={'q': query, 'type': content_type}
            )
            
            if response.status_code == 200:
                data = response.json()
                total_results = data.get('total', 0)
                logger.info(f"Found {total_results} results on Deezer")
                
                if total_results > 0 and data.get('data'):
                    item = data['data'][0]
                    if 'id' in item:
                        deezer_url = f"https://www.deezer.com/{content_type}/{item['id']}"
                        logger.info(f"Selected first result: {deezer_url}")
                        return deezer_url
                        
                logger.warning(f"No valid results found on Deezer for query: {query}")
                return None
                
            else:
                logger.error(f"Deezer API request failed: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error searching Deezer for {content_type} - {query}: {str(e)}", exc_info=True)
            return None

    async def search(self, query: str, search_type: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Search on Spotify"""
        try:
            logger.info(f"Searching Spotify - Type: {search_type}, Query: {query}, Limit: {limit}, Offset: {offset}")
            
            results = self.sp.search(
                q=query,
                type=search_type,
                limit=limit,
                offset=offset
            )
            
            items = results[f"{search_type}s"]['items']
            logger.info(f"Found {len(items)} {search_type}s on Spotify")
            return items
            
        except Exception as e:
            logger.error(f"Error searching Spotify for {search_type} - {query}: {str(e)}", exc_info=True)
            return []

    async def get_item_info(self, item_type: str, item_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a Spotify item"""
        try:
            logger.info(f"Getting Spotify item info - Type: {item_type}, ID: {item_id}")
            
            if item_type == 'track':
                info = self.sp.track(item_id)
                logger.info(f"Retrieved track info: {info.get('name', 'Unknown Track')}")
                return info
                
            elif item_type == 'album':
                info = self.sp.album(item_id)
                logger.info(f"Retrieved album info: {info.get('name', 'Unknown Album')}")
                return info
                
            elif item_type == 'playlist':
                info = self.sp.playlist(item_id)
                logger.info(f"Retrieved playlist info: {info.get('name', 'Unknown Playlist')}")
                return info
                
            else:
                logger.error(f"Unsupported item type: {item_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting {item_type} info for {item_id}: {str(e)}", exc_info=True)
            return None
