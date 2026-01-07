import os
import logging
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import Optional, Dict, Any, List

from ..config import settings

logger = logging.getLogger(__name__)


class SpotifyService:
    def __init__(self):
        """Initialize SpotifyService with API credentials"""
        try:
            self.client_id = settings.SPOTIFY_CLIENT_ID
            self.client_secret = settings.SPOTIFY_CLIENT_SECRET

            if not self.client_id or not self.client_secret:
                logger.error("Spotify credentials not found")
                raise ValueError("Missing Spotify credentials")

            self.sp = spotipy.Spotify(
                auth_manager=SpotifyClientCredentials(
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
            )
            logger.info("SpotifyService initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize SpotifyService: {str(e)}")
            raise

    async def search(
        self,
        query: str,
        search_type: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search on Spotify"""
        try:
            logger.info(f"Searching Spotify - Type: {search_type}, Query: {query}")

            results = self.sp.search(
                q=query,
                type=search_type,
                limit=limit,
                offset=offset
            )

            items = results[f"{search_type}s"]['items']
            processed_items = []

            for item in items:
                processed_item = self._process_search_result(item, search_type)
                if processed_item:
                    processed_items.append(processed_item)

            logger.info(f"Found {len(processed_items)} {search_type}s")
            return processed_items

        except Exception as e:
            logger.error(f"Error searching Spotify: {str(e)}")
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
                    'preview_url': item.get('preview_url'),
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
                        'name': item['owner'].get('display_name', 'Unknown')
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
                    'genres': item.get('genres', []),
                    'popularity': item.get('popularity', 0),
                    'images': item.get('images', []),
                    'type': 'artist'
                }
            return None
        except Exception as e:
            logger.error(f"Error processing search result: {str(e)}")
            return None

    async def get_item_info(self, item_type: str, item_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a Spotify item"""
        try:
            logger.info(f"Getting Spotify item info - Type: {item_type}, ID: {item_id}")

            if item_type == 'track':
                track = self.sp.track(item_id)
                return {
                    'id': track['id'],
                    'name': track['name'],
                    'artists': [{'id': artist['id'], 'name': artist['name']} for artist in track['artists']],
                    'main_artist': track['artists'][0]['name'],
                    'url': track['external_urls']['spotify'],
                    'duration_ms': track['duration_ms'],
                    'duration': self._format_duration(track['duration_ms']),
                    'explicit': track['explicit'],
                    'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'album': {
                        'id': track['album']['id'],
                        'name': track['album']['name'],
                        'release_date': track['album']['release_date'],
                        'images': track['album']['images']
                    },
                    'preview_url': track.get('preview_url'),
                    'popularity': track['popularity'],
                    'external_ids': track.get('external_ids', {}),
                    'type': 'track'
                }

            elif item_type == 'album':
                album = self.sp.album(item_id)
                tracks = self.sp.album_tracks(item_id)['items']
                return {
                    'id': album['id'],
                    'name': album['name'],
                    'artists': [{'id': artist['id'], 'name': artist['name']} for artist in album['artists']],
                    'main_artist': album['artists'][0]['name'],
                    'release_date': album['release_date'],
                    'total_tracks': album['total_tracks'],
                    'image': album['images'][0]['url'] if album['images'] else None,
                    'images': album['images'],
                    'tracks': [
                        {
                            'id': track['id'],
                            'name': track['name'],
                            'artist': album['artists'][0]['name'],
                            'duration_ms': track['duration_ms'],
                            'duration': self._format_duration(track['duration_ms']),
                            'track_number': track['track_number'],
                            'preview_url': track.get('preview_url')
                        }
                        for track in tracks
                    ],
                    'type': 'album',
                    'url': album['external_urls']['spotify']
                }

            elif item_type == 'playlist':
                playlist = self.sp.playlist(item_id)
                return {
                    'id': playlist['id'],
                    'name': playlist['name'],
                    'owner': {
                        'id': playlist['owner']['id'],
                        'name': playlist['owner'].get('display_name', 'Unknown')
                    },
                    'description': playlist.get('description'),
                    'total_tracks': playlist['tracks']['total'],
                    'image': playlist['images'][0]['url'] if playlist['images'] else None,
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
                        if item['track']
                    ],
                    'url': playlist['external_urls']['spotify'],
                    'type': 'playlist'
                }

            elif item_type == 'artist':
                artist = self.sp.artist(item_id)
                top_tracks = []
                albums = []
                related_artists = []

                try:
                    top_tracks_data = self.sp.artist_top_tracks(item_id, country='US')['tracks']
                    top_tracks = [
                        {
                            'id': track['id'],
                            'name': track['name'],
                            'artist': artist['name'],
                            'popularity': track['popularity'],
                            'preview_url': track.get('preview_url'),
                            'album': track['album']['name'],
                            'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                            'url': track['external_urls']['spotify']
                        }
                        for track in top_tracks_data
                    ]
                except Exception:
                    pass

                try:
                    albums_data = self.sp.artist_albums(item_id, album_type='album')['items']
                    albums = [
                        {
                            'id': album['id'],
                            'name': album['name'],
                            'artist': artist['name'],
                            'release_date': album['release_date'],
                            'total_tracks': album['total_tracks'],
                            'image': album['images'][0]['url'] if album['images'] else None,
                            'url': album['external_urls']['spotify']
                        }
                        for album in albums_data
                    ]
                except Exception:
                    pass

                try:
                    related_data = self.sp.artist_related_artists(item_id)['artists']
                    related_artists = [
                        {
                            'id': related['id'],
                            'name': related['name'],
                            'followers': related['followers']['total'],
                            'genres': related.get('genres', []),
                            'popularity': related.get('popularity', 0),
                            'image': related['images'][0]['url'] if related['images'] else None,
                            'url': related['external_urls']['spotify']
                        }
                        for related in related_data
                    ]
                except Exception:
                    pass

                return {
                    'id': artist['id'],
                    'name': artist['name'],
                    'followers': artist['followers']['total'],
                    'genres': artist.get('genres', []),
                    'popularity': artist.get('popularity', 0),
                    'image': artist['images'][0]['url'] if artist['images'] else None,
                    'url': artist['external_urls']['spotify'],
                    'type': 'artist',
                    'more_artist_info': {
                        'top_tracks': top_tracks,
                        'albums': albums,
                        'related_artists': related_artists
                    }
                }

            return None

        except Exception as e:
            logger.error(f"Error getting {item_type} info: {str(e)}")
            return None

    async def get_recommendations(self, track_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get track recommendations based on a seed track"""
        try:
            logger.info(f"Getting recommendations for track: {track_id}")
            
            # First try Spotify's recommendations API
            try:
                recommendations = self.sp.recommendations(
                    seed_tracks=[track_id],
                    limit=limit
                )
                
                if recommendations and recommendations.get('tracks'):
                    tracks = []
                    for track in recommendations['tracks']:
                        tracks.append({
                            'id': track['id'],
                            'name': track['name'],
                            'artists': [{'id': artist['id'], 'name': artist['name']} for artist in track['artists']],
                            'artist': track['artists'][0]['name'],
                            'album': track['album']['name'],
                            'album_id': track['album']['id'],
                            'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                            'duration_ms': track['duration_ms'],
                            'duration': self._format_duration(track['duration_ms']),
                            'preview_url': track.get('preview_url'),
                            'popularity': track.get('popularity', 0),
                            'url': track['external_urls']['spotify']
                        })
                    
                    logger.info(f"Found {len(tracks)} recommendations from Spotify API")
                    return tracks
            except Exception as rec_error:
                logger.warning(f"Recommendations API failed, falling back to artist tracks: {str(rec_error)}")
            
            # Fallback: Get artist's top tracks from the same track
            try:
                track_info = self.sp.track(track_id)
                if track_info and track_info.get('artists'):
                    artist_id = track_info['artists'][0]['id']
                    top_tracks_data = self.sp.artist_top_tracks(artist_id, country='US')['tracks']
                    
                    tracks = []
                    for track in top_tracks_data:
                        if track['id'] != track_id:  # Exclude the current track
                            tracks.append({
                                'id': track['id'],
                                'name': track['name'],
                                'artists': [{'id': artist['id'], 'name': artist['name']} for artist in track['artists']],
                                'artist': track['artists'][0]['name'],
                                'album': track['album']['name'],
                                'album_id': track['album']['id'],
                                'image': track['album']['images'][0]['url'] if track['album']['images'] else None,
                                'duration_ms': track['duration_ms'],
                                'duration': self._format_duration(track['duration_ms']),
                                'preview_url': track.get('preview_url'),
                                'popularity': track.get('popularity', 0),
                                'url': track['external_urls']['spotify']
                            })
                            if len(tracks) >= limit:
                                break
                    
                    logger.info(f"Found {len(tracks)} similar tracks from artist")
                    return tracks
            except Exception as artist_error:
                logger.error(f"Artist fallback also failed: {str(artist_error)}")
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}")
            return []

    def _format_duration(self, ms: int) -> str:
        """Format milliseconds to MM:SS format"""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"


# Singleton instance
_spotify_service: Optional[SpotifyService] = None


def get_spotify_service() -> SpotifyService:
    global _spotify_service
    if _spotify_service is None:
        _spotify_service = SpotifyService()
    return _spotify_service
