import os
import json
from ytmusicapi import YTMusic
from typing import Optional, Dict, Any, List
from logger import get_logger

logger = get_logger(__name__)

class YTMusicService:
    def __init__(self):
        """Initialize YTMusicService"""
        try:
            self.yt = YTMusic()
            logger.info("YTMusicService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize YTMusicService: {str(e)}", exc_info=True)
            raise

    async def search(self, query: str, search_type: str, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Search on YTMusic"""
        import asyncio
        
        def _fetch():
            logger.info(f"Searching YTMusic - Type: {search_type}, Query: {query}, Limit: {limit}")
            
            # Map search_type to YTMusic filter
            filter_map = {
                'track': 'songs',
                'album': 'albums',
                'playlist': 'playlists',
                'artist': 'artists'
            }
            
            filter_param = filter_map.get(search_type)
            results = self.yt.search(query=query, filter=filter_param, limit=limit)
            
            processed_items = []
            for item in results:
                processed_item = self._process_search_result(item, search_type)
                if processed_item:
                    processed_items.append(processed_item)
            
            logger.info(f"Found {len(processed_items)} {search_type}s on YTMusic")
            return processed_items

        try:
            return await asyncio.to_thread(_fetch)
        except Exception as e:
            logger.error(f"Error searching YTMusic for {search_type} - {query}: {str(e)}", exc_info=True)
            return []

    def _process_search_result(self, item: Dict[str, Any], item_type: str) -> Optional[Dict[str, Any]]:
        """Process and standardize search result item"""
        try:
            if item_type == 'track' and item['resultType'] == 'song':
                artists = [{'id': a.get('id'), 'name': a.get('name')} for a in item.get('artists', [])]
                main_artist = artists[0]['name'] if artists else 'Unknown'
                duration_str = item.get('duration', '0:00')
                
                return {
                    'id': item['videoId'],
                    'name': item['title'],
                    'artists': artists,
                    'main_artist': main_artist,
                    'duration': duration_str,
                    'album': {
                        'id': item.get('album', {}).get('id'),
                        'name': item.get('album', {}).get('name', 'Unknown'),
                    },
                    'type': 'track',
                    'url': f"https://music.youtube.com/watch?v={item['videoId']}"
                }
            elif item_type == 'album' and item['resultType'] == 'album':
                artists = [{'id': a.get('id'), 'name': a.get('name')} for a in item.get('artists', [])]
                main_artist = artists[0]['name'] if artists else 'Unknown'
                
                return {
                    'id': item['browseId'],
                    'name': item['title'],
                    'artists': artists,
                    'main_artist': main_artist,
                    'release_date': item.get('year'),
                    'type': 'album',
                    'url': f"https://music.youtube.com/browse/{item['browseId']}"
                }
            elif item_type == 'playlist' and item['resultType'] == 'playlist':
                return {
                    'id': item['browseId'],
                    'name': item['title'],
                    'owner': {
                        'name': item.get('author', 'Unknown')
                    },
                    'total_tracks': item.get('itemCount'),
                    'type': 'playlist',
                    'url': f"https://music.youtube.com/playlist?list={item['browseId']}"
                }
            elif item_type == 'artist' and item['resultType'] == 'artist':
                return {
                    'id': item['browseId'],
                    'name': item['artist'],
                    'type': 'artist',
                    'url': f"https://music.youtube.com/channel/{item['browseId']}"
                }
            return None
        except Exception as e:
            logger.error(f"Error processing search result: {str(e)}", exc_info=True)
            return None

    async def get_item_info(self, item_type: str, item_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a YTMusic item"""
        import asyncio
        
        def _fetch():
            logger.info(f"Getting YTMusic item info - Type: {item_type}, ID: {item_id}")
            
            if item_type == 'track':
                track = self.yt.get_song(item_id)
                details = track.get('videoDetails', {})
                
                # Default values
                title = details.get('title', 'Unknown')
                artist = details.get('author', 'Unknown')
                album_name = 'Unknown'
                release_year = 'Unknown'
                genre = 'Pop' # Default genre
                lyrics_text = ''
                
                # Fetch lyrics
                try:
                    watch = self.yt.get_watch_playlist(videoId=item_id)
                    lyrics_id = watch.get('lyrics')
                    if lyrics_id:
                        lyrics_dict = self.yt.get_lyrics(lyrics_id)
                        lyrics_text = lyrics_dict.get('lyrics', '')
                except Exception as e:
                    logger.error(f"Could not fetch lyrics for {item_id}: {e}")
                
                # Search to get album and year since get_song doesn't provide them easily
                try:
                    search_results = self.yt.search(f"{title} {artist}", filter="songs", limit=1)
                    if search_results:
                        res = search_results[0]
                        if res.get('videoId') == item_id or res.get('title') == title:
                            album_name = res.get('album', {}).get('name', 'Unknown')
                            release_year = res.get('year', 'Unknown')
                except Exception as e:
                    logger.error(f"Could not fetch extended metadata for {item_id}: {e}")

                # Find highest quality image
                thumbnails = details.get('thumbnail', {}).get('thumbnails', [])
                image_url = thumbnails[-1].get('url') if thumbnails else None
                # Replace url parameter to get highest res without crop
                if image_url and 'w120' in image_url:
                    image_url = image_url.replace('w120', 'w1080').replace('h120', 'h1080')
                elif image_url and '=' in image_url:
                    # e.g. ...=w120-h120-l90-rj
                    base_url = image_url.split('=')[0]
                    image_url = f"{base_url}=w1080-h1080-l90-rj"
                
                info = {
                    'id': details.get('videoId', item_id),
                    'name': title,
                    'artists': [{'name': artist, 'id': details.get('channelId')}],
                    'main_artist': artist,
                    'url': f"https://music.youtube.com/watch?v={item_id}",
                    'duration': str(details.get('lengthSeconds', 0)) + "s",
                    'explicit': False,
                    'album': {
                        'name': album_name,
                        'release_date': release_year
                    },
                    'release_year': release_year,
                    'genre': genre,
                    'lyrics': lyrics_text,
                    'popularity': 0,
                    'type': 'track',
                    'image': image_url
                }
                
                return info
                
            elif item_type == 'album':
                album = self.yt.get_album(item_id)
                tracks = album.get('tracks', [])
                
                thumbnails = album.get('thumbnails', [])
                image_url = thumbnails[-1].get('url') if thumbnails else None
                
                info = {
                    'id': item_id,
                    'name': album.get('title', 'Unknown'),
                    'artists': [{'name': a.get('name')} for a in album.get('artists', [])],
                    'main_artist': album.get('artists', [{}])[0].get('name', 'Unknown') if album.get('artists') else 'Unknown',
                    'release_date': album.get('year', 'Unknown'),
                    'total_tracks': album.get('trackCount', len(tracks)),
                    'tracks': [
                        {
                            'id': t.get('videoId'),
                            'name': t.get('title'),
                            'artist': album.get('artists', [{}])[0].get('name', 'Unknown') if album.get('artists') else 'Unknown',
                            'duration': t.get('duration', '0:00'),
                            'track_number': i + 1,
                        }
                        for i, t in enumerate(tracks) if t.get('videoId')
                    ],
                    'type': 'album',
                    'url': f"https://music.youtube.com/browse/{item_id}",
                    'image': image_url
                }
                
                return info
                
            elif item_type == 'playlist':
                playlist = self.yt.get_playlist(item_id)
                tracks = playlist.get('tracks', [])
                
                thumbnails = playlist.get('thumbnails', [])
                image_url = thumbnails[-1].get('url') if thumbnails else None
                
                info = {
                    'id': item_id,
                    'name': playlist.get('title', 'Unknown'),
                    'owner': {
                        'name': playlist.get('author', {}).get('name', 'Unknown')
                    },
                    'description': playlist.get('description', ''),
                    'total_tracks': playlist.get('trackCount', len(tracks)),
                    'tracks': [
                        {
                            'id': t.get('videoId'),
                            'name': t.get('title'),
                            'artist': t.get('artists', [{}])[0].get('name', 'Unknown') if t.get('artists') else 'Unknown',
                            'duration': t.get('duration', '0:00'),
                        }
                        for t in tracks if t.get('videoId')
                    ],
                    'url': f"https://music.youtube.com/playlist?list={item_id}",
                    'type': 'playlist',
                    'image': image_url
                }
                
                return info
            
            elif item_type == 'artist':
                artist = self.yt.get_artist(item_id)
                top_tracks = artist.get('songs', {}).get('results', [])
                albums = artist.get('albums', {}).get('results', [])
                related = artist.get('related', {}).get('results', [])
                
                thumbnails = artist.get('thumbnails', [])
                image_url = thumbnails[-1].get('url') if thumbnails else None
                
                artist_info = {
                    'id': item_id,
                    'name': artist.get('name', 'Unknown'),
                    'followers': artist.get('subscribers', 'Unknown'),
                    'genres': [],
                    'popularity': 0,
                    'url': f"https://music.youtube.com/channel/{item_id}",
                    'type': 'artist',
                    'image': image_url,
                    'more_artist_info': {
                        'top_tracks': [
                            {
                                'id': t.get('videoId'),
                                'name': t.get('title'),
                                'artist': artist.get('name', 'Unknown'),
                                'album': t.get('album', {}).get('name', 'Unknown'),
                                'url': f"https://music.youtube.com/watch?v={t.get('videoId')}"
                            } for t in top_tracks if t.get('videoId')
                        ],
                        'albums': [
                            {
                                'id': a.get('browseId'),
                                'name': a.get('title'),
                                'artist': artist.get('name', 'Unknown'),
                                'release_date': a.get('year', 'Unknown'),
                                'url': f"https://music.youtube.com/browse/{a.get('browseId')}"
                            } for a in albums if a.get('browseId')
                        ],
                        'related_artists': [
                            {
                                'id': r.get('browseId'),
                                'name': r.get('title'),
                                'url': f"https://music.youtube.com/channel/{r.get('browseId')}"
                            } for r in related if r.get('browseId')
                        ]
                    }
                }
                
                return artist_info
            
            else:
                logger.error(f"Unsupported item type: {item_type}")
                return None

        try:
            return await asyncio.to_thread(_fetch)
        except Exception as e:
            logger.error(f"Error getting {item_type} info for {item_id}: {str(e)}", exc_info=True)
            return None
