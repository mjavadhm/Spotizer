from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Tuple, Dict, Any, List

class MusicView:
    @staticmethod
    def format_search_results(results: List[Dict[str, Any]], search_type: str, query: str, page: int = 1) -> Tuple[str, InlineKeyboardMarkup]:
        """Format search results with pagination"""
        buttons = []
        
        # Create buttons for each result
        for item in results:
            if search_type == "track":
                artists = ", ".join([artist['name'] for artist in item['artists']])
                text = f"🎵 {item['name']} - {artists}"
            elif search_type == "album":
                text = f"📀 {item['name']} by {item['main_artist']}"
            else:  # playlist
                text = f"📑 {item['name']} ({item['total_tracks']} tracks)"
                
            # Truncate long titles
            if len(text) > 60:
                text = text[:57] + "..."
                
            buttons.append([
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"select:{search_type}:{item['id']}"
                )
            ])

        # Add navigation buttons if needed
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Previous",
                    callback_data=f"page:{page-1}:{search_type}:{query}"
                )
            )
        
        nav_buttons.append(
            InlineKeyboardButton(
                text="❌",
                callback_data="delete"
            )
        )
        
        # Add next button if there are more results
        if len(results) == 5:  # If we got a full page, assume there might be more
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Next ➡️",
                    callback_data=f"page:{page+1}:{search_type}:{query}"
                )
            )
        
        if nav_buttons:
            buttons.append(nav_buttons)

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Create message text
        text = f"Search results for '{query}' ({search_type.capitalize()}s):\nPage {page}"
        
        return text, keyboard

    @staticmethod
    def format_track_info(track: Dict[str, Any]) -> str:
        """Format track information"""
        artists = ", ".join([artist['name'] for artist in track['artists']])
        
        info = [
            f"🎵 *{track['name']}*",
            f"👤 Artist: {artists}",
            f"💿 Album: {track['album']['name']}",
            f"⏱ Duration: {track['duration']}",
            f"📅 Release: {track['album']['release_date']}"
        ]
        
        if 'audio_features' in track:
            features = track['audio_features']
            info.extend([
                f"\n🎼 *Audio Features:*",
                f"💃 Danceability: {features['danceability']}",
                f"⚡️ Energy: {features['energy']}",
                f"🎹 Key: {features['key']}",
                f"⏰ Tempo: {int(features['tempo'])} BPM"
            ])
        
        return "\n".join(info)

    @staticmethod
    def get_track_keyboard(track: Dict[str, Any]) -> InlineKeyboardMarkup:
        """Create keyboard for track view"""
        buttons = [
            [InlineKeyboardButton(
                text="⬇️ Download",
                callback_data=f"download:track:{track['id']}"
            )],
            [InlineKeyboardButton(
                text="❌ Close",
                callback_data="delete"
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def format_album_info(album: Dict[str, Any]) -> str:
        """Format album information"""
        artists = ", ".join([artist['name'] for artist in album['artists']])
        
        info = [
            f"💿 *{album['name']}*",
            f"👤 Artist: {artists}",
            f"📅 Release: {album['release_date']}",
            f"🎵 Tracks: {album['total_tracks']}"
        ]
        
        return "\n".join(info)

    @staticmethod
    def get_album_keyboard(album: Dict[str, Any]) -> InlineKeyboardMarkup:
        """Create keyboard for album view"""
        buttons = [
            [InlineKeyboardButton(
                text="📋 View Tracks",
                callback_data=f"view:album:tracks:{album['id']}"
            )],
            [InlineKeyboardButton(
                text="⬇️ Download Album",
                callback_data=f"download:album:{album['id']}"
            )],
            [InlineKeyboardButton(
                text="❌ Close",
                callback_data="delete"
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def format_playlist_info(playlist: Dict[str, Any]) -> str:
        """Format playlist information"""
        info = [
            f"📑 *{playlist['name']}*",
            f"👤 Created by: {playlist['owner']['name']}",
            f"🎵 Tracks: {playlist['total_tracks']}"
        ]
        
        if playlist.get('description'):
            info.insert(1, f"📝 {playlist['description']}")
        
        return "\n".join(info)

    @staticmethod
    def get_playlist_keyboard(playlist: Dict[str, Any]) -> InlineKeyboardMarkup:
        """Create keyboard for playlist view"""
        buttons = [
            [InlineKeyboardButton(
                text="📋 View Tracks",
                callback_data=f"view:playlist:tracks:{playlist['id']}"
            )],
            [InlineKeyboardButton(
                text="⬇️ Download Playlist",
                callback_data=f"download:playlist:{playlist['id']}"
            )],
            [InlineKeyboardButton(
                text="❌ Close",
                callback_data="delete"
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def get_back_keyboard(content_type: str, item_id: str) -> InlineKeyboardMarkup:
        """Create keyboard with back button"""
        buttons = [
            [InlineKeyboardButton(
                text="⬅️ Back",
                callback_data=f"select:{content_type}:{item_id}"
            )],
            [InlineKeyboardButton(
                text="❌ Close",
                callback_data="delete"
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def format_tracks_list(tracks: List[Dict[str, Any]], parent_info: Dict[str, Any], content_type: str) -> str:
        """Format list of tracks for album or playlist"""
        if content_type == "album":
            header = f"Tracks in album '{parent_info['name']}' by {parent_info['main_artist']}:\n\n"
            track_format = lambda t, i: f"{t['track_number']}. {t['name']} ({t['duration']})"
        else:  # playlist
            header = f"Tracks in playlist '{parent_info['name']}':\n\n"
            track_format = lambda t, i: f"{i}. {t['name']} - {t['main_artist']} ({t['duration']})"
        
        track_list = [track_format(track, i+1) for i, track in enumerate(tracks)]
        
        return header + "\n".join(track_list)
