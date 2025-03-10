import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import logging
from typing import Dict, Any, Optional, List, Tuple
import os
from dotenv import load_dotenv
load_dotenv()
client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')


# Configure logger
logger = logging.getLogger(__name__)

# Initialize Spotify client (you'll need to set these environment variables or pass them in)
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=client_id,
    client_secret=client_secret
))

class Artist:
    def __init__(self, artist_id: str) -> None:
        self.artist_id = artist_id
        self.artist_details = get_artist_details(artist_id)
        self.artist_name = self.artist_details['name']
        self.artist_thumbnail = self.artist_details['thumbnail']
        self.artist_url = self.artist_details['url']
        self.artist_popularity = self.artist_details['popularity']
        self.artist_followers = self.artist_details['followers']
        self.artist_genres = self.artist_details['genres']
        self.related_artists = self.artist_details.get('related_artists', [])
        self.top_tracks = self.artist_details.get('top_tracks', [])
        self.albums = self.artist_details.get('albums', [])
        self.albums = self.albums[:5]  # Limit to first 5 albums

    def get_artist_detail(self):
        return self.artist_details

    def get_artist_name(self):
        return self.artist_name

    def get_artist_thumbnail(self):
        return self.artist_thumbnail

    def get_artist_url(self):
        return self.artist_url

    def get_artist_popularity(self):
        return self.artist_popularity

    def get_artist_followers(self):
        return self.artist_followers

    def get_artist_genres(self):
        return self.artist_genres

    def get_related_artists(self):
        return self.related_artists

    def get_top_tracks(self):
        return self.top_tracks

    def get_albums(self):
        return self.albums

    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        return get_spotify_item_info("album", album_id)

    def get_track(self, track_id: str) -> Optional[Dict[str, Any]]:
        return get_spotify_item_info("track", track_id)

    def get_playlist(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        return get_spotify_item_info("playlist", playlist_id)

    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        return get_artist_details(artist_id)


async def playlist_creator(musics,file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name, duration ,path in musics:
            f.write(f"#EXTINF:{duration},{name}\n")
            f.write(f"{path}\n")

def get_spotify_item_info(item_type: str, item_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves detailed information about a Spotify item.
    
    Args:
        item_type (str): The type of item ('track', 'album', or 'playlist')
        item_id (str): The Spotify ID of the item
        
    Returns:
        Optional[Dict[str, Any]]: Dictionary containing the item's information or None if not found
    """
    try:
        if item_type == "track":
            # Get track info
            track = sp.track(item_id)
            
            # Get album info for additional details
            album_id = track['album']['id']
            album = sp.album(album_id)
            
            # Extract relevant information
            result = {
                'id': track['id'],
                'name': track['name'],
                'artists': [{'id': artist['id'], 'name': artist['name']} for artist in track['artists']],
                'main_artist': track['artists'][0]['name'],
                'duration_ms': track['duration_ms'],
                'duration': format_duration(track['duration_ms']),
                'explicit': track['explicit'],
                'album': {
                    'id': track['album']['id'],
                    'name': track['album']['name'],
                    'release_date': track['album']['release_date'],
                    'total_tracks': track['album']['total_tracks'],
                    'images': track['album']['images']
                },
                'thumbnail': get_best_image(track['album']['images']),
                'preview_url': track['preview_url'],
                'popularity': track['popularity'],
                'url': track['external_urls']['spotify']
            }
            
            # Get audio features for additional track information
            try:
                audio_features = sp.audio_features(item_id)[0]
                if audio_features:
                    result['audio_features'] = {
                        'danceability': audio_features['danceability'],
                        'energy': audio_features['energy'],
                        'key': audio_features['key'],
                        'tempo': audio_features['tempo'],
                        'time_signature': audio_features['time_signature']
                    }
            except:
                # Audio features are not critical, continue if this fails
                pass
                
            return result
            
        elif item_type == "album":
            # Get album info
            album = sp.album(item_id)
            
            # Get tracks in album
            tracks = sp.album_tracks(item_id)
            
            # Extract relevant information
            result = {
                'id': album['id'],
                'name': album['name'],
                'artists': [{'id': artist['id'], 'name': artist['name']} for artist in album['artists']],
                'main_artist': album['artists'][0]['name'],
                'release_date': album['release_date'],
                'total_tracks': album['total_tracks'],
                'type': album['album_type'],  # album, single, compilation
                'images': album['images'],
                'thumbnail': get_best_image(album['images']),
                'url': album['external_urls']['spotify'],
                'tracks': []
            }
            
            # Add track information
            for track in tracks['items']:
                result['tracks'].append({
                    'id': track['id'],
                    'name': track['name'],
                    'artists': [{'id': artist['id'], 'name': artist['name']} for artist in track['artists']],
                    'main_artist': track['artists'][0]['name'],
                    'duration_ms': track['duration_ms'],
                    'duration': format_duration(track['duration_ms']),
                    'track_number': track['track_number'],
                    'explicit': track['explicit'],
                    'preview_url': track['preview_url']
                })
                
            return result
            
        elif item_type == "playlist":
            # Get playlist info
            playlist = sp.playlist(item_id)
            
            # Extract relevant information
            result = {
                'id': playlist['id'],
                'name': playlist['name'],
                'description': playlist['description'],
                'owner': {
                    'id': playlist['owner']['id'],
                    'name': playlist['owner']['display_name']
                },
                'total_tracks': playlist['tracks']['total'],
                'images': playlist['images'],
                'thumbnail': get_best_image(playlist['images']),
                'url': playlist['external_urls']['spotify'],
                'tracks': []
            }
            
            # Add track information (up to first 100 tracks)
            for item in playlist['tracks']['items']:
                track = item['track']
                if track:  # Sometimes tracks can be None due to availability
                    result['tracks'].append({
                        'id': track['id'],
                        'name': track['name'],
                        'artists': [{'id': artist['id'], 'name': artist['name']} for artist in track['artists']],
                        'main_artist': track['artists'][0]['name'] if track['artists'] else "Unknown",
                        'album': {
                            'id': track['album']['id'],
                            'name': track['album']['name']
                        },
                        'duration_ms': track['duration_ms'],
                        'duration': format_duration(track['duration_ms']),
                        'explicit': track['explicit'],
                        'added_at': item['added_at'],
                        'preview_url': track['preview_url']
                    })
                    
            # For long playlists, indicate if there are more tracks
            if playlist['tracks']['total'] > len(result['tracks']):
                result['more_tracks_available'] = True
                result['tracks_fetched'] = len(result['tracks'])
            
            return result
        
        else:
            logger.error(f"Invalid item type: {item_type}")
            return None
            
    except Exception as e:
        logger.error(f"Error retrieving Spotify item ({item_type} - {item_id}): {str(e)}")
        return None

def get_artist_details(artist_id: str, minimal: bool = False, include_top_tracks: bool = True, include_albums: bool = True) -> Optional[Dict[str, Any]]:
    """
    Retrieves detailed information about a Spotify artist.
    
    Args:
        artist_id (str): The Spotify ID of the artist
        minimal (bool): If True, returns only basic artist information
        include_top_tracks (bool): If True, includes the artist's top tracks
        include_albums (bool): If True, includes the artist's albums
        
    Returns:
        Optional[Dict[str, Any]]: Dictionary containing the artist's information or None if not found
    """
    try:
        # Get basic artist info
        artist = sp.artist(artist_id)
        
        # Start with basic information
        result = {
            'id': artist['id'],
            'name': artist['name'],
            'popularity': artist['popularity'],
            'genres': artist['genres'],
            'followers': artist['followers']['total'],
            'images': artist['images'],
            'thumbnail': get_best_image(artist['images']),
            'url': artist['external_urls']['spotify']
        }
        
        # For minimal requests, return only basic info
        if minimal:
            return result
            
        # Add related artists
        try:
            related_artists = sp.artist_related_artists(artist_id)['artists']
            result['related_artists'] = [
                {
                    'id': related['id'],
                    'name': related['name'],
                    'thumbnail': get_best_image(related['images'])
                }
                for related in related_artists[:5]  # Limit to top 5 related artists
            ]
        except:
            # Related artists are not critical, continue if this fails
            pass
        
        # Add top tracks if requested
        if include_top_tracks:
            try:
                top_tracks = sp.artist_top_tracks(artist_id)['tracks']
                result['top_tracks'] = [
                    {
                        'id': track['id'],
                        'name': track['name'],
                        'album': {
                            'id': track['album']['id'],
                            'name': track['album']['name'],
                            'release_date': track['album']['release_date'],
                            'thumbnail': get_best_image(track['album']['images'])
                        },
                        'duration_ms': track['duration_ms'],
                        'duration': format_duration(track['duration_ms']),
                        'popularity': track['popularity'],
                        'preview_url': track['preview_url']
                    }
                    for track in top_tracks
                ]
            except:
                # Top tracks are not critical, continue if this fails
                pass
        
        # Add albums if requested
        if include_albums:
            try:
                albums = sp.artist_albums(
                    artist_id, 
                    album_type='album,single',
                    limit=50
                )['items']
                
                # Process and deduplicate albums (Spotify often has multiple versions)
                seen_names = set()
                unique_albums = []
                
                for album in albums:
                    # Create a normalized name for deduplication (remove special editions, etc.)
                    norm_name = album['name'].lower().split('(')[0].split('[')[0].strip()
                    
                    if norm_name not in seen_names:
                        seen_names.add(norm_name)
                        unique_albums.append({
                            'id': album['id'],
                            'name': album['name'],
                            'type': album['album_type'],
                            'release_date': album['release_date'],
                            'total_tracks': album['total_tracks'],
                            'thumbnail': get_best_image(album['images'])
                        })
                
                result['albums'] = unique_albums
            except:
                # Albums are not critical, continue if this fails
                pass
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving artist details ({artist_id}): {str(e)}")
        return None


def format_duration(ms: int) -> str:
    """Format milliseconds to MM:SS format"""
    seconds = ms // 1000
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{seconds:02d}"

def get_best_image(images: List[Dict[str, Any]]) -> Optional[str]:
    """
    Get the best image URL from a list of Spotify image objects.
    Tries to find a medium-sized image or returns the first one.
    
    Args:
        images (List[Dict[str, Any]]): List of Spotify image objects
        
    Returns:
        Optional[str]: URL of the best image or None if no images available
    """
    if not images:
        return None
        
    # Sort by size (width)
    sorted_images = sorted(images, key=lambda x: x.get('width', 0))
    
    # If we have at least 3 images, return the middle one (medium size)
    if len(sorted_images) >= 3:
        return sorted_images[len(sorted_images) // 2]['url']
    
    # Otherwise return the first one
    return sorted_images[0]['url']

