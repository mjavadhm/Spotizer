import os
import requests
import json
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import Optional, Dict, Any, List
from logger import get_logger

logger = get_logger(__name__)

class SpotifyService:
    def __init__(self):
        """Initialize SpotifyService with API credentials"""
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
                
                deezer_url = self._search_on_deezer('track', query)
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
                
                deezer_url = self._search_on_deezer('album', query)
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

    def _search_on_deezer(self, content_type: str, query: str) -> Optional[str]:
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
            
            # Extract items based on search type
            items = results[f"{search_type}s"]['items']
            
            # Process items to standardize format
            processed_items = []
            for item in items:
                processed_item = self._process_search_result(item, search_type)
                if processed_item:
                    processed_items.append(processed_item)
            
            logger.info(f"Found {len(processed_items)} {search_type}s on Spotify")
            return processed_items
            
        except Exception as e:
            logger.error(f"Error searching Spotify for {search_type} - {query}: {str(e)}", exc_info=True)
            return []

    def _process_search_result(self, item: Dict[str, Any], item_type: str) -> Optional[Dict[str, Any]]:
        """Process and standardize search result item"""
        try:
            if item_type == 'track':
                return {
                    'id': item['id'],
                    'name': item['name'],
                    'artists': [{'id': artist['id'], 'name': artist['name']} for artist in item['artists']],
                    'main_artist': item['artists'][0]['name'],
                    'duration_ms': item['duration_ms'],
                    'duration': self._format_duration(item['duration_ms']),
                    'album': {
                        'id': item['album']['id'],
                        'name': item['album']['name'],
                        'images': item['album']['images']
                    },
                    'preview_url': item['preview_url'],
                    'type': 'track'
                }
            elif item_type == 'album':
                return {
                    'id': item['id'],
                    'name': item['name'],
                    'artists': [{'id': artist['id'], 'name': artist['name']} for artist in item['artists']],
                    'main_artist': item['artists'][0]['name'],
                    'total_tracks': item['total_tracks'],
                    'release_date': item['release_date'],
                    'images': item['images'],
                    'type': 'album'
                }
            elif item_type == 'playlist':
                return {
                    'id': item['id'],
                    'name': item['name'],
                    'owner': {
                        'id': item['owner']['id'],
                        'name': item['owner']['display_name']
                    },
                    'total_tracks': item['tracks']['total'],
                    'images': item['images'],
                    'type': 'playlist'
                }
            elif item_type == 'artist':
                return {
                    'id': item['id'],
                    'name': item['name'],
                    'followers': item['followers']['total'],
                    'genres': item['genres'],
                    'popularity': item['popularity'],
                    'images': item['images'],
                    'type': 'artist'
                }
            return None
        except Exception as e:
            logger.error(f"Error processing search result: {str(e)}", exc_info=True)
            return None

    async def get_item_info(self, item_type: str, item_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a Spotify item"""
        try:
            logger.info(f"Getting Spotify item info - Type: {item_type}, ID: {item_id}")
            
            if item_type == 'track':
                track = self.sp.track(item_id)
                # audio_features = self.sp.audio_features(item_id)[0]
                info = {
                    'id': track['id'],
                    'name': track['name'],
                    'artists': [{'id': artist['id'], 'name': artist['name']} for artist in track['artists']],
                    'main_artist': track['artists'][0]['name'],
                    'url': track['external_urls']['spotify'],
                    'duration_ms': track['duration_ms'],
                    'duration': self._format_duration(track['duration_ms']),
                    'explicit': track['explicit'],
                    'image': track['album']['images'][0]['url'],
                    'album': {
                        'id': track['album']['id'],
                        'name': track['album']['name'],
                        'release_date': track['album']['release_date'],
                        'images': track['album']['images']
                    },
                    'preview_url': track['preview_url'],
                    'popularity': track['popularity'],
                    'type': 'track'
                }
                
                # if audio_features:
                #     info['audio_features'] = {
                #         'danceability': audio_features['danceability'],
                #         'energy': audio_features['energy'],
                #         'key': audio_features['key'],
                #         'tempo': audio_features['tempo']
                #     }
                
                logger.info(f"Retrieved track info: {info['name']}")
                return info
                
            elif item_type == 'album':
                album = self.sp.album(item_id)
                tracks = self.sp.album_tracks(item_id)['items']
                info = {
                    'id': album['id'],
                    'name': album['name'],
                    'artists': [{'id': artist['id'], 'name': artist['name']} for artist in album['artists']],
                    'main_artist': album['artists'][0]['name'],
                    'release_date': album['release_date'],
                    'total_tracks': album['total_tracks'],
                    'image': album['images'][0]['url'],
                    'images': album['images'],
                    'tracks': [
                        {
                            'id': track['id'],
                            'name': track['name'],
                            'artist': album['artists'][0]['name'],
                            'duration_ms': track['duration_ms'],
                            'duration': self._format_duration(track['duration_ms']),
                            'track_number': track['track_number'],
                            'preview_url': track['preview_url']
                        }
                        for track in tracks
                    ],
                    'type': 'album',
                    'url': album['external_urls']['spotify'],
                }
                
                logger.info(f"Retrieved album info: {info['name']}")
                return info
                
            elif item_type == 'playlist':
                playlist = self.sp.playlist(item_id)
                info = {
                    'id': playlist['id'],
                    'name': playlist['name'],
                    'owner': {
                        'id': playlist['owner']['id'],
                        'name': playlist['owner']['display_name']
                    },
                    'description': playlist['description'],
                    'total_tracks': playlist['tracks']['total'],
                    'image': playlist['images'][0]['url'],
                    'images': playlist['images'],
                    'tracks': [
                        {
                            'id': item['track']['id'],
                            'name': item['track']['name'],
                            'artists': [{'id': artist['id'], 'name': artist['name']} for artist in item['track']['artists']],
                            'artist': item['track']['artists'][0]['name'],
                            'duration_ms': item['track']['duration_ms'],
                            'duration': self._format_duration(item['track']['duration_ms']),
                            'added_at': item['added_at']
                        }
                        for item in playlist['tracks']['items']
                        if item['track']  # Some tracks might be None
                    ],
                    'url': playlist['external_urls']['spotify'],
                    'type': 'playlist'
                    
                }
                
                logger.info(f"Retrieved playlist info: {info['name']}")
                return info
            
            elif item_type == 'artist':
                artist = self.sp.artist(item_id)
                try:
                    top_tracks = self.sp.artist_top_tracks(item_id, country='US')['tracks']
                except:
                    top_tracks = None
                try:
                    albums = self.sp.artist_albums(item_id, album_type='album')['items']
                except:
                    albums = None
                                
                try:
                    related_artists = self.sp.artist_related_artists(item_id)['artists']
                except:
                    related_artists = None
                            
                artist_info = {
                    'id': artist['id'],
                    'name': artist['name'],
                    'followers': artist['followers']['total'],
                    'genres': artist['genres'],
                    'popularity': artist['popularity'],
                    'image': artist['images'][0]['url'] if artist['images'] else None,
                    'url': artist['external_urls']['spotify'],
                    'type': 'artist'
                }
                
                if top_tracks:
                    top_tracks_info = [
                        {
                            'id': track['id'],
                            'name': track['name'],
                            'artist': artist['name'],
                            'popularity': track['popularity'],
                            'preview_url': track['preview_url'],
                            'album': track['album']['name'],
                            'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                            'url': track['external_urls']['spotify']
                        }
                        for track in top_tracks
                    ]
                else:
                    top_tracks_info = None

                if albums:
                    albums_info = [
                        {
                            'id': album['id'],
                            'name': album['name'],
                            'artist': artist['name'],
                            'release_date': album['release_date'],
                            'total_tracks': album['total_tracks'],
                            'image': album['images'][0]['url'] if album['images'] else None,
                            'url': album['external_urls']['spotify']
                        }
                        for album in albums
                    ]
                else:
                    albums_info = None

                if related_artists:
                    related_info = [
                        {
                            'id': related['id'],
                            'name': related['name'],
                            'followers': related['followers']['total'],
                            'genres': related['genres'],
                            'popularity': related['popularity'],
                            'image': related['images'][0]['url'] if related['images'] else None,
                            'url': related['external_urls']['spotify']
                        }
                        for related in related_artists
                    ]
                else:
                    related_info = None

                logger.info(f"Retrieved full artist info for {artist_info['name']}")
                
                artist_info.update({
                    'more_artist_info': {
                        'top_tracks': top_tracks_info,
                        'albums': albums_info,
                        'related_artists': related_info
                    }
                })
                
                return artist_info
            elif item_type == 'related':
                related_artists = self.sp.artist_related_artists(item_id)['artists']
                info = [
                    {
                        'id': artist['id'],
                        'name': artist['name'],
                        'followers': artist['followers']['total'],
                        'genres': artist['genres'],
                        'popularity': artist['popularity'],
                        'image': artist['images'][0]['url'] if artist['images'] else None,
                        'url': artist['external_urls']['spotify'],
                        'type': 'artist'
                    }
                    for artist in related_artists
                ]
                logger.info(f"Retrieved {len(info)} related artists for artist ID {item_id}")
                return info
            else:
                logger.error(f"Unsupported item type: {item_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting {item_type} info for {item_id}: {str(e)}", exc_info=True)
            return None

    def _format_duration(self, ms: int) -> str:
        """Format milliseconds to MM:SS format"""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
