import aiogram
import os
from sqlalchemy.future import select
from database.session import async_session_maker
from models.base import Playlist, PlaylistTrack
from services.deezer_service import DeezerService
import aiogram.types
from bot import bot
from logger import get_logger
from views.playlist_view import PlaylistView

logger = get_logger(__name__)

class PlayListController:
    def __init__(self):
        self.deezer_service = DeezerService()

    @staticmethod
    async def get_user_playlists(user_id: int) -> tuple[bool, list]:
        """Get all playlists for a specific user."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(Playlist).where(Playlist.user_id == user_id)
            )
            playlists = result.scalars().all()
            return True, playlists

    @staticmethod
    async def create_playlist(user_id: int, name: str) -> tuple[bool, str]:
        """Create a new playlist for a specific user."""
        async with async_session_maker() as session:
            async with session.begin():
                playlist = Playlist(user_id=user_id, name=name)
                session.add(playlist)
            await session.commit()
            return True, "Playlist created successfully"

    @staticmethod
    async def delete_playlist(user_id: int, playlist_id: int) -> tuple[bool, str]:
        """Delete a playlist for a specific user."""
        async with async_session_maker() as session:
            async with session.begin():
                playlist = await session.get(Playlist, playlist_id)
                if playlist and playlist.user_id == user_id:
                    await session.delete(playlist)
                    await session.commit()
                    logger.info(f"Deleted playlist '{playlist_id}' for user {user_id}")
                    return True, "Playlist deleted successfully"
                return False, "Playlist not found or permission denied"

    @staticmethod
    async def update_playlist(
        user_id: int, playlist_id: int, name: str, description: str
    ) -> tuple[bool, str]:
        """Update a playlist for a specific user."""
        async with async_session_maker() as session:
            async with session.begin():
                playlist = await session.get(Playlist, playlist_id)
                if playlist and playlist.user_id == user_id:
                    playlist.name = name
                    playlist.description = description
                    await session.commit()
                    return True, "Playlist updated successfully"
                return False, "Playlist not found or permission denied"

    @staticmethod
    async def add_to_playlist(
        user_id: int, playlist_id: int, track_id: int
    ) -> tuple[bool, str]:
        """Add a track to a playlist for a specific user."""
        async with async_session_maker() as session:
            async with session.begin():
                playlist = await session.get(Playlist, playlist_id)
                if playlist and playlist.user_id == user_id:
                    playlist_track = PlaylistTrack(
                        playlist_id=playlist_id, track_deezer_id=track_id
                    )
                    session.add(playlist_track)
                    await session.commit()
                    return True, "Track added to playlist successfully"
                return False, "Playlist not found or permission denied"

    async def add_action(self, user_id, callback_query):
        """Handle add to playlist action."""
        try:
            action = callback_query.data.split(":")[2]
            if action == "get_playlist":
                track_id = callback_query.data.split(":")[3]
                success, playlists = await self.get_user_playlists(user_id)
                if success:
                    keyboard, text = PlaylistView.get_playlist_for_add_keyboard(
                        playlists, track_id
                    )
                    await callback_query.message.answer(text=text, reply_markup=keyboard)
                else:
                    await callback_query.message.answer("You have no playlists.")

            else:
                track_id = callback_query.data.split(":")[3]
                spotify_url = f"https://open.spotify.com/track/{track_id}"
                url = await self.deezer_service.convert_to_deezer(spotify_url)
                if not url:
                    await callback_query.answer("Could not find track on Deezer")
                    return
                content_type, deezer_id = self.deezer_service.extract_info_from_url(url)
                if not deezer_id:
                    await callback_query.answer("Could not process track")
                    return
                playlist_id = int(callback_query.data.split(":")[2])  # Convert to int
                success, message = await self.add_to_playlist(
                    user_id, playlist_id, int(deezer_id)  # Ensure deezer_id is also int
                )
                await callback_query.answer(message)

                if success:
                    await callback_query.message.answer(
                        "Track added to playlist successfully"
                    )
                else:
                    await callback_query.message.answer(
                        "Failed to add track to playlist"
                    )

            await callback_query.answer()
        except Exception as e:
            logger.error(f"Error adding action for user {user_id}: {str(e)}", exc_info=True)
            await callback_query.answer("Error adding action")

    @staticmethod
    async def remove_from_playlist(
        user_id: int, playlist_id: int, playlist_track_id: int
    ) -> tuple[bool, str]:
        """Remove a track from a playlist."""
        async with async_session_maker() as session:
            async with session.begin():
                playlist = await session.get(Playlist, playlist_id)
                if playlist and playlist.user_id == user_id:
                    playlist_track = await session.get(PlaylistTrack, playlist_track_id)
                    if playlist_track and playlist_track.playlist_id == playlist_id:
                        await session.delete(playlist_track)
                        await session.commit()
                        logger.info(f"Removed track {playlist_track_id} from playlist {playlist_id}")
                        return True, "Track removed from playlist successfully"
                    return False, "Track not found in playlist"
                return False, "Playlist not found or permission denied"

    async def get_playlist_tracks(self, user_id: int, playlist_id: int) -> tuple[bool, list]:
        """Get all tracks in a playlist with full track information."""
        async with async_session_maker() as session:
            playlist = await session.get(Playlist, playlist_id)
            if not playlist or playlist.user_id != user_id:
                return False, []
            
            result = await session.execute(
                select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id)
            )
            playlist_tracks = result.scalars().all()
            
            # Get track info from Deezer
            tracks_info = []
            for pt in playlist_tracks:
                try:
                    track_info = await self.deezer_service.get_deezer_info('track', pt.track_deezer_id)
                    if track_info:
                        track_info['playlist_track_id'] = pt.playlist_track_id
                        track_info['added_at'] = pt.added_at
                        tracks_info.append(track_info)
                except Exception as e:
                    logger.error(f"Error getting track info for {pt.track_deezer_id}: {str(e)}")
                    continue
            
            return True, tracks_info

    async def create_playlist_and_add_track(
        self, user_id: int, playlist_name: str, track_id: int
    ) -> tuple[bool, str]:
        """Create a new playlist and add a track to it."""
        async with async_session_maker() as session:
            async with session.begin():
                # Create playlist
                playlist = Playlist(user_id=user_id, name=playlist_name)
                session.add(playlist)
                await session.flush()  # Get the playlist_id
                
                # Add track to playlist
                playlist_track = PlaylistTrack(
                    playlist_id=playlist.playlist_id,
                    track_deezer_id=track_id
                )
                session.add(playlist_track)
                await session.commit()
                
                logger.info(f"Created playlist '{playlist_name}' and added track {track_id} for user {user_id}")
                return True, "Playlist created and track added successfully"
