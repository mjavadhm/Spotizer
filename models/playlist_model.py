import aiogram
from typing import Dict, List, Optional, Any
from datetime import datetime
from database.connection import get_connection
from logger import get_logger
import psycopg2.extras

logger = get_logger(__name__)

class PlaylistModel:
    def create_playlist(self, user_id: int, name: str, description: str = None) -> Optional[int]:
        """Create a new playlist for a user and return its ID."""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO playlists (user_id, name, description) VALUES (%s, %s, %s) RETURNING playlist_id",
                        (user_id, name, description)
                    )
                    playlist_id = cur.fetchone()[0]
                    conn.commit()
                    logger.info(f"Created playlist '{name}' for user {user_id}")
                    return playlist_id
        except Exception as e:
            logger.error(f"Failed to create playlist: {e}")
            return None
    
    def get_user_playlists(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all playlists for a specific user."""
        try:
            with get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(
                        "SELECT playlist_id, name, description FROM playlists WHERE user_id = %s",
                        (user_id,)
                    )
                    playlists = cur.fetchall()
                    logger.info(f"Retrieved {len(playlists)} playlists for user {user_id}")
                    return [dict(p) for p in playlists]  # تبدیل به dict
        except Exception as e:
            logger.error(f"Failed to get user playlists: {e}")
            return []

    def add_track_to_playlist(self, playlist_id: int, track_deezer_id: int) -> bool:
        """Add a track to a playlist."""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO playlist_tracks (playlist_id, track_deezer_id) VALUES (%s, %s)",
                        (playlist_id, track_deezer_id)
                    )
                    conn.commit()
                    logger.info(f"Added track {track_deezer_id} to playlist {playlist_id}")
                    return True
        except Exception as e:
            logger.error(f"Failed to add track to playlist: {e}")
            return False

    def get_playlist_tracks(self, playlist_id: int) -> List[Dict[str, Any]]:
        """Get all tracks within a single playlist."""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT track_deezer_id FROM playlist_tracks WHERE playlist_id = %s",
                        (playlist_id,)
                    )
                    tracks = cur.fetchall()
                    logger.info(f"Retrieved {len(tracks)} tracks for playlist {playlist_id}")
                    return tracks
        except Exception as e:
            logger.error(f"Failed to get playlist tracks: {e}")
            return []

    def delete_playlist(self, user_id: int, playlist_id: int) -> bool:
        """Delete a playlist for a specific user."""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM playlists WHERE user_id = %s AND playlist_id = %s",
                        (user_id, playlist_id)
                    )
                    conn.commit()
                    logger.info(f"Deleted playlist {playlist_id} for user {user_id}")
                    return True
        except Exception as e:
            logger.error(f"Failed to delete playlist: {e}")
            return False

    def update_playlist(self, user_id: int, playlist_id: int, name: str, description: str) -> bool:
        """Update a playlist for a specific user."""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE playlists SET name = %s, description = %s WHERE user_id = %s AND playlist_id = %s",
                        (name, description, user_id, playlist_id)
                    )
                    conn.commit()
                    logger.info(f"Updated playlist {playlist_id} for user {user_id}")
                    return True
        except Exception as e:
            logger.error(f"Failed to update playlist: {e}")
            return False

    def get_playlist(self, user_id: int, playlist_id: int) -> Dict[str, Any]:
        """Get a specific playlist for a user."""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT playlist_id, name, description FROM playlists WHERE user_id = %s AND playlist_id = %s",
                        (user_id, playlist_id)
                    )
                    playlist = cur.fetchone()
                    if playlist:
                        logger.info(f"Retrieved playlist {playlist_id} for user {user_id}")
                        return {
                            "id": playlist[0],
                            "name": playlist[1],
                            "description": playlist[2]
                        }
                    else:
                        logger.warning(f"Playlist {playlist_id} not found for user {user_id}")
                        return {}
        except Exception as e:
            logger.error(f"Failed to get playlist: {e}")
            return {}

    def add_to_playlist(self, user_id, playlist_id, track_id):
        """Add a track to a specific playlist."""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO playlist_tracks (playlist_id, track_deezer_id) VALUES (%s, %s)",
                        (playlist_id, track_id)
                    )
                    conn.commit()
                    logger.info(f"Added track {track_id} to playlist {playlist_id} for user {user_id}")
                    return True
        except Exception as e:
            logger.error(f"Failed to add track to playlist: {e}")
            return False