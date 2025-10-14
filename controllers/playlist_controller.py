import aiogram
import os
from models.download_model import DownloadModel
from models.user_model import UserModel
from models.playlist_model import PlaylistModel
import aiogram.types
from bot import bot
from logger import get_logger
from views.playlist_view import PlaylistView

logger = get_logger(__name__)

class PlayListController:
    def __init__(self):
        self.download_model = DownloadModel()
        self.user_model = UserModel()
        self.playlist_model = PlaylistModel()

    async def get_user_playlists(self, user_id: int) -> tuple[bool, list]:
        """
        Get all playlists for a specific user

        Args:
            user_id (int): ID of the user

        Returns:
            tuple[bool, list]: Success status and list of playlists
        """
        try:
            playlists = self.playlist_model.get_user_playlists(user_id)
            if playlists:
                logger.info(f"Retrieved {len(playlists)} playlists for user {user_id}")
                return True, playlists
            else:
                logger.warning(f"No playlists found for user {user_id}")
                return False, []
        except Exception as e:
            logger.error(f"Error getting playlists for user {user_id}: {str(e)}", exc_info=True)
            return False, []

    async def create_playlist(self, user_id: int, name: str) -> tuple[bool, str]:
        """
        Create a new playlist for a specific user

        Args:
            user_id (int): ID of the user
            name (str): Name of the playlist

        Returns:
            tuple[bool, str]: Success status and message
        """
        try:
            self.playlist_model.create_playlist(user_id, name)
            logger.info(f"Created playlist '{name}' for user {user_id}")
            return True, "Playlist created successfully"
        except Exception as e:
            logger.error(f"Error creating playlist for user {user_id}: {str(e)}", exc_info=True)
            return False, "Error creating playlist"

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

    async def update_playlist(self, user_id: int, playlist_id: int, name: str, description: str) -> tuple[bool, str]:
        """
        Update a playlist for a specific user

        Args:
            user_id (int): ID of the user
            playlist_id (int): ID of the playlist
            name (str): New name for the playlist

        Returns:
            tuple[bool, str]: Success status and message
        """
        try:
            self.playlist_model.update_playlist(user_id, playlist_id, name, description)
            logger.info(f"Updated playlist '{playlist_id}' for user {user_id} to '{name}'")
            return True, "Playlist updated successfully"
        except Exception as e:
            logger.error(f"Error updating playlist for user {user_id}: {str(e)}", exc_info=True)
            return False, "Error updating playlist"

    async def add_to_playlist(self, user_id: int, playlist_id: int, track_id: int) -> tuple[bool, str]:
        """
        Add a track to a playlist for a specific user

        Args:
            user_id (int): ID of the user
            playlist_id (int): ID of the playlist
            track_id (int): ID of the track to add

        Returns:
            tuple[bool, str]: Success status and message
        """
        try:
            self.playlist_model.add_to_playlist(user_id, playlist_id, track_id)
            logger.info(f"Added track '{track_id}' to playlist '{playlist_id}' for user {user_id}")
            return True, "Track added to playlist successfully"
        except Exception as e:
            logger.error(f"Error adding track to playlist for user {user_id}: {str(e)}", exc_info=True)
            return False, "Error adding track to playlist"


    async def add_action(self, user_id, callback_query):
        """Handle add to playlist action"""
        try:
            action = callback_query.data.split(":")[2]
            if action == "get_playlist":
                track_id = callback_query.data.split(":")[3]
                playlists = self.playlist_model.get_user_playlists(user_id)

                keyboard, text = PlaylistView.get_playlist_for_add_keyboard(playlists, track_id)
                await callback_query.message.answer(text=text, reply_markup=keyboard)

            else:
                track_id = callback_query.data.split(":")[3]
                playlist_id = callback_query.data.split(":")[2]
                success, message = await self.add_to_playlist(user_id, playlist_id, track_id)
                await callback_query.answer(message)

                if success:
                    await callback_query.message.answer("Track added to playlist successfully")
                else:
                    await callback_query.message.answer("Failed to add track to playlist")

            await callback_query.answer()
        except Exception as e:
            logger.error(f"Error adding action for user {user_id}: {str(e)}", exc_info=True)
            await callback_query.answer("Error adding action")