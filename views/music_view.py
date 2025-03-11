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
            elif search_type == "artist":
                text = f"👤 {item['name']}"
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
            f"🎵 *{track['name']}*\n",
            f"👤 Artist: {artists}\n",
            f"💿 Album: {track['album']['name']}\n",
            f"⏱ Duration: {track['duration']}",
            f"📅 Release: {track['album']['release_date']}"
        ]
        text = f"""🎵 *Track:* [{track['name']}]({track['url']})

👤 *Artist:* {track['main_artist']}

💿 *Album:* {track['album']['name']}

📅 *Released:* {track['album']['release_date']}

⏱ *Duration:* {track['duration']}

🔥 *Popularity:* {track['popularity']}/100

🔞 *Explicit:* {'Yes' if track['explicit'] else 'No'}"""
        
        if 'audio_features' in track:
            features = track['audio_features']
            info.extend([
                f"\n🎼 *Audio Features:*",
                f"💃 Danceability: {features['danceability']}",
                f"⚡️ Energy: {features['energy']}",
                f"🎹 Key: {features['key']}",
                f"⏰ Tempo: {int(features['tempo'])} BPM"
            ])
            text += f"""
🎛 *Audio Features:*
• Danceability: {features['danceability']:.2f}
• Energy: {features['energy']:.2f}
• Tempo: {features['tempo']:.0f} BPM
• Key: {features['key']}
• Time Signature: {features['time_signature']}/4"""
        
        # return "\n".join(info)
        return text

    @staticmethod
    def get_track_keyboard(track: Dict[str, Any]) -> InlineKeyboardMarkup:
        """Create keyboard for track view"""
        buttons = [
            [InlineKeyboardButton(
                text="⬇️ Download",
                callback_data=f"download:track:{track['id']}"
            )],
            [InlineKeyboardButton(
                text=f"🎨 Artist:{track['main_artist']}",
                callback_data=f"select:artist:{track['artists'][0]['id']}"
            )],
            [InlineKeyboardButton(
                text=f"📀 Album:{track['album']['name']}",
                callback_data=f"select:album:{track['album']['id']}"
            )],
            [InlineKeyboardButton(
                text="❌",
                callback_data="delete"
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def format_album_info(album: Dict[str, Any]) -> str:
        """Format album information"""
        artists = ", ".join([artist['name'] for artist in album['artists']])
        
        info = [
            f"📀 *Album:* [{album['name']}]({album['url']})\n",
            f"👤 *Artist:* {artists}\n",
            f"📅 *Release:* {album['release_date']}\n",
            f"🎵 *Tracks:* {album['total_tracks']}"
        ]
        
        return "\n".join(info)

    @staticmethod
    def get_album_keyboard(album: Dict[str, Any]) -> InlineKeyboardMarkup:
        """Create keyboard for album view"""
        buttons = [
            [InlineKeyboardButton(
                text="⬇️ Download Album",
                callback_data=f"download:album:{album['id']}"
            )],
            [InlineKeyboardButton(
                text="📋 View Tracks",
                callback_data=f"view:album:tracks:{album['id']}:1"
            )],
            [InlineKeyboardButton(
                text=f"🎨 Artist:{album['main_artist']}",
                callback_data=f"select:artist:{album['artists'][0]['id']}"
            )],
            [InlineKeyboardButton(
                text="❌",
                callback_data="delete"
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def format_playlist_info(playlist: Dict[str, Any]) -> str:
        """Format playlist information"""
        info = [
            f"📑 *Playlist:* [{playlist['name']}]({playlist['url']})\n",
            f"ℹ️ *Description:* {playlist['description']}\n",
            f"🎵 *Tracks:* {playlist['total_tracks']}"
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
                callback_data=f"view:playlist:tracks:{playlist['id']}:1"
            )],
            [InlineKeyboardButton(
                text="⬇️ Download Playlist",
                callback_data=f"download:playlist:{playlist['id']}"
            )],
            [InlineKeyboardButton(
                text="❌",
                callback_data="delete"
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def format_artist_info(artist: Dict[str, Any]) -> str:
        """Format artist information"""
        genres_text = ", ".join(artist['genres']) if artist['genres'] else "N/A"
        
        info = [
            f"🎨 *Artist:* [{artist['name']}]({artist['url']})\n",
            f"👥 *Followers:* {artist['followers']:,}\n",
            f"🔥 *Popularity:* {artist['popularity']}/100\n",
            f"🎭 *Genres:* {genres_text}"
        ]
        
        return "\n".join(info)

    @staticmethod
    def get_artist_keyboard(artist: Dict[str, Any]) -> InlineKeyboardMarkup:
        """Create keyboard for artist view"""
        buttons = []
        if artist['top_track']:
            buttons.append(
            InlineKeyboardButton(
                    text="🔝 Top Tracks",
                    callback_data=f"view:artist:top_tracks:{artist['id']}:1"
                )
            )
        if artist['album']:
            buttons.append(InlineKeyboardButton(
                    text="💿 Albums",
                    callback_data=f"view:artist:albums:{artist['id']}:1"
                )
            )
        if artist['related_artists']:
            buttons.append(InlineKeyboardButton(
                    text="👥 Related Artists",
                    callback_data=f"view:artist:related:{artist['id']}:1"
                )
            )
        buttons.append(
            InlineKeyboardButton(
                text="❌",
                callback_data="delete"
            )
        )
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
                text="❌",
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
        elif content_type == "artist":
            header = f"Top '{parent_info['name']}' tracks:\n\n"
            track_format = lambda t, i: f"{i}. {t['name']} - {t['main_artist']} ({t['duration']})"
        else:  # playlist
            header = f"Top '{parent_info['name']}' tracks:\n\n"
            track_format = lambda t, i: f"{i}. {t['name']} - {t['main_artist']} ({t['duration']})"
        
        track_list = [track_format(track, i+1) for i, track in enumerate(tracks)]
        
        return header + "\n".join(track_list)
    
    def format_albums_list(albums: List[Dict[str, Any]], parent_info: Dict[str, Any], content_type: str) -> str:
        """Format list of tracks for album or playlist"""
        if content_type == "album":
            header = f"Tracks in album '{parent_info['name']}' by {parent_info['main_artist']}:\n\n"
            track_format = lambda t, i: f"{t['track_number']}. {t['name']} ({t['duration']})"
        else:  # playlist
            header = f"Tracks in playlist '{parent_info['name']}':\n\n"
            track_format = lambda t, i: f"{i}. {t['name']} - {t['main_artist']} ({t['duration']})"
        
        track_list = [track_format(track, i+1) for i, track in enumerate(albums)]
        
        return header + "\n".join(track_list)

    def format_artists_list(artists: List[Dict[str, Any]], parent_info: Dict[str, Any], content_type: str) -> str:
        """Format list of tracks for album or playlist"""
        if content_type == "album":
            header = f"Tracks in album '{parent_info['name']}' by {parent_info['main_artist']}:\n\n"
            track_format = lambda t, i: f"{t['track_number']}. {t['name']} ({t['duration']})"
        else:  # playlist
            header = f"Tracks in playlist '{parent_info['name']}':\n\n"
            track_format = lambda t, i: f"{i}. {t['name']} - {t['main_artist']} ({t['duration']})"
        
        track_list = [track_format(track, i+1) for i, track in enumerate(artists)]
        
        return header + "\n".join(track_list)
    @staticmethod
    def get_list_keyboard(items: List[Dict[str, Any]], content_type: str, action: str, page: int = 1) -> InlineKeyboardMarkup:
        buttons = []
        i = 0
        for item in items:
            if i < (page-1)*8 :
                continue
            if action == 'related':
                button_text = f"{item['name']}"
            else:
                button_text = f"{item['name']} - {item['artist']}"
            
            callback_data = f"select:{action}:{item['id']}:{page}"
            buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
            i+=1
            if i > (page)*8:
                break
        remaining_items = len(items) - (page)*8
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="⬅️ Previous",
                    callback_data=f"view:{content_type}:{action}:{page-1}"
                )
            )
        
        nav_buttons.append(
            InlineKeyboardButton(
                text="❌",
                callback_data="delete"
            )
        )
        
        
        if remaining_items > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Next ➡️",
                    callback_data=f"view:{content_type}:{action}:{page+1}"
                )
            )
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        return keyboard

