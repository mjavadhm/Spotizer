from sqlalchemy.future import select

from bale_bot.database import bale_async_session_maker
from bale_bot.database.models import BalePlaylist, BalePlaylistTrack
from bale_bot.views.playlist_view import PlaylistView
from services.deezer_service import DeezerService
from logger import get_logger

logger = get_logger(__name__)


class BalePlaylistController:
    """Playlist controller for Bale bot - uses separate Bale database"""

    def __init__(self):
        self.deezer_service = DeezerService()

    async def create_playlist(self, user_id: int, name: str, description: str = None):
        """Create a new playlist for user."""
        async with bale_async_session_maker() as session:
            try:
                # Check if playlist with same name exists
                result = await session.execute(
                    select(BalePlaylist).where(
                        BalePlaylist.user_id == user_id,
                        BalePlaylist.name == name
                    )
                )
                existing = result.scalars().first()
                
                if existing:
                    return False, "A playlist with this name already exists"
                
                playlist = BalePlaylist(
                    user_id=user_id,
                    name=name,
                    description=description
                )
                session.add(playlist)
                await session.commit()
                await session.refresh(playlist)
                
                logger.info(f"Created Bale playlist '{name}' for user {user_id}")
                return True, playlist
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error creating Bale playlist: {str(e)}", exc_info=True)
                return False, str(e)

    async def get_user_playlists(self, user_id: int):
        """Get all playlists for a user."""
        async with bale_async_session_maker() as session:
            try:
                result = await session.execute(
                    select(BalePlaylist)
                    .where(BalePlaylist.user_id == user_id)
                    .order_by(BalePlaylist.created_at.desc())
                )
                playlists = result.scalars().all()
                return True, playlists
                
            except Exception as e:
                logger.error(f"Error getting Bale playlists: {str(e)}", exc_info=True)
                return False, str(e)

    async def add_to_playlist(self, user_id: int, playlist_id: int, track_deezer_id: int):
        """Add a track to a playlist."""
        async with bale_async_session_maker() as session:
            try:
                # Verify playlist belongs to user
                result = await session.execute(
                    select(BalePlaylist).where(
                        BalePlaylist.playlist_id == playlist_id,
                        BalePlaylist.user_id == user_id
                    )
                )
                playlist = result.scalars().first()
                
                if not playlist:
                    return False, "Playlist not found"
                
                # Check if track already in playlist
                result = await session.execute(
                    select(BalePlaylistTrack).where(
                        BalePlaylistTrack.playlist_id == playlist_id,
                        BalePlaylistTrack.track_deezer_id == track_deezer_id
                    )
                )
                existing = result.scalars().first()
                
                if existing:
                    return False, "Track already in playlist"
                
                track = BalePlaylistTrack(
                    playlist_id=playlist_id,
                    track_deezer_id=track_deezer_id
                )
                session.add(track)
                await session.commit()
                
                logger.info(f"Added track {track_deezer_id} to Bale playlist {playlist_id}")
                return True, "Track added to playlist"
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error adding to Bale playlist: {str(e)}", exc_info=True)
                return False, str(e)

    async def remove_from_playlist(self, user_id: int, playlist_id: int, playlist_track_id: int):
        """Remove a track from a playlist."""
        async with bale_async_session_maker() as session:
            try:
                # Verify playlist belongs to user
                result = await session.execute(
                    select(BalePlaylist).where(
                        BalePlaylist.playlist_id == playlist_id,
                        BalePlaylist.user_id == user_id
                    )
                )
                playlist = result.scalars().first()
                
                if not playlist:
                    return False, "Playlist not found"
                
                # Delete track
                result = await session.execute(
                    select(BalePlaylistTrack).where(
                        BalePlaylistTrack.playlist_track_id == playlist_track_id
                    )
                )
                track = result.scalars().first()
                
                if track:
                    await session.delete(track)
                    await session.commit()
                    return True, "Track removed"
                else:
                    return False, "Track not found"
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error removing from Bale playlist: {str(e)}", exc_info=True)
                return False, str(e)

    async def delete_playlist(self, user_id: int, playlist_id: int):
        """Delete a playlist."""
        async with bale_async_session_maker() as session:
            try:
                result = await session.execute(
                    select(BalePlaylist).where(
                        BalePlaylist.playlist_id == playlist_id,
                        BalePlaylist.user_id == user_id
                    )
                )
                playlist = result.scalars().first()
                
                if playlist:
                    await session.delete(playlist)
                    await session.commit()
                    return True, "Playlist deleted"
                else:
                    return False, "Playlist not found"
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error deleting Bale playlist: {str(e)}", exc_info=True)
                return False, str(e)

    async def get_playlist_tracks(self, user_id: int, playlist_id: int):
        """Get all tracks in a playlist with their details."""
        async with bale_async_session_maker() as session:
            try:
                # Verify playlist belongs to user
                result = await session.execute(
                    select(BalePlaylist).where(
                        BalePlaylist.playlist_id == playlist_id,
                        BalePlaylist.user_id == user_id
                    )
                )
                playlist = result.scalars().first()
                
                if not playlist:
                    return False, "Playlist not found"
                
                # Get tracks
                result = await session.execute(
                    select(BalePlaylistTrack)
                    .where(BalePlaylistTrack.playlist_id == playlist_id)
                    .order_by(BalePlaylistTrack.added_at.desc())
                )
                playlist_tracks = result.scalars().all()
                
                # Fetch track details from Deezer
                tracks = []
                for pt in playlist_tracks:
                    try:
                        track_info = await self.deezer_service.get_track_info(pt.track_deezer_id)
                        if track_info:
                            tracks.append({
                                'id': pt.track_deezer_id,
                                'playlist_track_id': pt.playlist_track_id,
                                'title': track_info.get('title', 'Unknown'),
                                'artist': {'name': track_info.get('artist', {}).get('name', 'Unknown')},
                                'duration': track_info.get('duration', 0)
                            })
                    except Exception as e:
                        logger.error(f"Error getting track info: {str(e)}")
                        tracks.append({
                            'id': pt.track_deezer_id,
                            'playlist_track_id': pt.playlist_track_id,
                            'title': 'Unknown Track',
                            'artist': {'name': 'Unknown Artist'},
                            'duration': 0
                        })
                
                return True, tracks
                
            except Exception as e:
                logger.error(f"Error getting Bale playlist tracks: {str(e)}", exc_info=True)
                return False, str(e)

    async def create_playlist_and_add_track(self, user_id: int, name: str, track_deezer_id: int):
        """Create a playlist and add a track to it."""
        success, result = await self.create_playlist(user_id, name)
        if not success:
            return False, result
        
        playlist = result
        success, result = await self.add_to_playlist(user_id, playlist.playlist_id, track_deezer_id)
        if not success:
            return False, result
        
        return True, "Playlist created and track added"

    async def add_action(self, user_id: int, callback_query):
        """Handle playlist add action from callback."""
        try:
            parts = callback_query.data.split(":")
            if parts[2] == "get_playlist":
                # Show playlist selection
                track_id = parts[3]
                success, playlists = await self.get_user_playlists(user_id)
                keyboard, text = PlaylistView.get_playlist_for_add_keyboard(playlists if success else [], track_id)
                await callback_query.message.answer(text, reply_markup=keyboard)
                await callback_query.answer()
            else:
                # Add to specific playlist
                playlist_id = int(parts[2])
                track_id = parts[3]
                success, message = await self.add_to_playlist(user_id, playlist_id, int(track_id))
                await callback_query.answer(message, show_alert=not success)
                
        except Exception as e:
            logger.error(f"Error in add_action: {str(e)}", exc_info=True)
            await callback_query.answer("Error adding to playlist", show_alert=True)
