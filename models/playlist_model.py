import aiogram
from typing import Dict, List, Optional, Any
from datetime import datetime
from database.connection import get_connection
from logger import get_logger

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
    # def get_user_playlists(self, user_id: int) -> List[Dict[str, Any]]:
    #     """Get all playlists for a specific user."""
        

    # def add_track_to_playlist(self, playlist_id: int, track_deezer_id: int) -> bool:
    #     """Add a track to a playlist."""
        

    # def get_playlist_tracks(self, playlist_id: int) -> List[Dict[str, Any]]:
    #     """Get all tracks within a single playlist."""
        