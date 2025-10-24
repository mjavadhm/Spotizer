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

    # async def delete_playlist(self, user_id: int, playlist_id: int) -> tuple[bool, str]:
    #     """
    #     Delete a playlist for a specific user

    #     Args:
    #         user_id (int): ID of the user
    #         playlist_id (int): ID of the playlist

    #     Returns:
    #         tuple[bool, str]: Success status and message
    #     """
    #     try:
    #         self.playlist_model.delete_playlist(user_id, playlist_id)
    #         logger.info(f"Deleted playlist '{playlist_id}' for user {user_id}")
    #         return True, "Playlist deleted successfully"
    #     except Exception as e:
    #         logger.error(f"Error deleting playlist for user {user_id}: {str(e)}", exc_info=True)
    #         return False, "Error deleting playlist"

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
                url = self.deezer_service.convert_to_deezer(spotify_url)
                content_type, deezer_id = self.deezer_service.extract_info_from_url(url)
                playlist_id = callback_query.data.split(":")[2]
                success, message = await self.add_to_playlist(
                    user_id, playlist_id, deezer_id
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
