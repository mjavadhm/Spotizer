from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class MusicView:
    @staticmethod
    def format_track_info(track):
        """Format track information for display"""
        # Format audio features if available
        audio_features = ""
        if 'audio_features' in track:
            af = track['audio_features']
            audio_features = f"""
🎛 *Audio Features:*
• Danceability: {af['danceability']:.2f}
• Energy: {af['energy']:.2f}
• Tempo: {af['tempo']:.0f} BPM
• Key: {af['key']}
• Time Signature: {af['time_signature']}/4"""

        text = f"""🎵 *Track:* [{track['name']}]({track['url']})

👤 *Artist:* {track['main_artist']}

💿 *Album:* {track['album']['name']}

📅 *Released:* {track['album']['release_date']}

⏱ *Duration:* {track['duration']}

🔥 *Popularity:* {track['popularity']}/100

🔞 *Explicit:* {'Yes' if track['explicit'] else 'No'}
{audio_features}"""

        return text

    @staticmethod
    def get_track_keyboard(track):
        """Create keyboard for track interactions"""
        buttons = [
            [InlineKeyboardButton(text="📥 Download", callback_data=f"download:track:{track['id']}")],
            [InlineKeyboardButton(text="🎨 Artist", callback_data=f"select:artist:{track['artists'][0]['id']}")],
            [InlineKeyboardButton(text="📀 Album", callback_data=f"select:album:{track['album']['id']}")],
            [InlineKeyboardButton(text="❌", callback_data="delete")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def format_album_info(album):
        """Format album information for display"""
        # Format tracks list (shortened)
        tracks_preview = ""
        for i, track in enumerate(album['tracks'][:3], 1):
            tracks_preview += f"{i}. {track['name']} - {track['duration']}\n"
        
        if len(album['tracks']) > 3:
            tracks_preview += f"and {len(album['tracks']) - 3} more tracks"

        text = f"""📀 *Album:* [{album['name']}]({album['url']})

👤 *Artist:* {album['main_artist']}

📅 *Released:* {album['release_date']}

🎵 *Tracks:* {album['total_tracks']}

📑 *Type:* {album['type'].capitalize()}

*Preview:*
{tracks_preview}"""

        return text

    @staticmethod
    def get_album_keyboard(album):
        """Create keyboard for album interactions"""
        buttons = [
            [InlineKeyboardButton(text="📥 Download Album", callback_data=f"download:album:{album['id']}")],
            [InlineKeyboardButton(text=f"🎨 Artist:{album['main_artist']}", 
                                callback_data=f"select:artist:{album['artists'][0]['id']}")],
            [InlineKeyboardButton(text="🎵 View Tracks", callback_data=f"view:album:tracks:{album['id']}:1")],
            [InlineKeyboardButton(text="❌", callback_data="delete")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def format_artist_info(artist):
        """Format artist information for display"""
        # Format genres list
        genres_text = ""
        if artist.artist_genres:
            genres_text = ", ".join(artist.artist_genres[:3])
            if len(artist.artist_genres) > 3:
                genres_text += f" and {len(artist.artist_genres) - 3} more"
        else:
            genres_text = "Not available"

        text = f"""🎨 *Artist:* [{artist.artist_name}]({artist.artist_url})

👥 *Followers:* {artist.artist_followers:,}

🔥 *Popularity:* {artist.artist_popularity}/100

🎭 *Genres:* {genres_text}"""

        return text

    @staticmethod
    def get_artist_keyboard(artist):
        """Create keyboard for artist interactions"""
        buttons = [
            [InlineKeyboardButton(text="🔝 Top Tracks", callback_data=f"view:artist:top_tracks:{artist.artist_id}:1")],
            [InlineKeyboardButton(text="💿 Albums", callback_data=f"view:artist:albums:{artist.artist_id}:1")]
        ]
        
        if artist.related_artists:
            buttons.append([InlineKeyboardButton(text="👥 Related Artists", 
                                               callback_data=f"view:artist:related:{artist.artist_id}:1")])
        
        buttons.append([InlineKeyboardButton(text="❌", callback_data="delete")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def format_playlist_info(playlist):
        """Format playlist information for display"""
        text = f"""📑 *Playlist:* [{playlist['name']}]({playlist['url']})

👤 *Creator:* {playlist['owner']['name']}

ℹ️ *Description:* {playlist['description']}

🎵 *Tracks:* {playlist['total_tracks']}"""

        return text

    @staticmethod
    def get_playlist_keyboard(playlist):
        """Create keyboard for playlist interactions"""
        buttons = [
            [InlineKeyboardButton(text="🎵 View Tracks", callback_data=f"view:playlist:tracks:{playlist['id']}:1")],
            [InlineKeyboardButton(text="📥 Download Playlist", callback_data=f"download:playlist:{playlist['id']}")],
            [InlineKeyboardButton(text="❌", callback_data="delete")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def get_pagination_keyboard(current_page, total_pages, base_callback, item_id):
        """Create pagination keyboard"""
        buttons = []
        nav_buttons = []

        if current_page > 1:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️ Previous", 
                                   callback_data=f"{base_callback}:{item_id}:{current_page-1}")
            )

        nav_buttons.append(
            InlineKeyboardButton(text=f"📄 {current_page}/{total_pages}", 
                               callback_data="page_info")
        )

        if current_page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton(text="Next ➡️", 
                                   callback_data=f"{base_callback}:{item_id}:{current_page+1}")
            )

        if nav_buttons:
            buttons.append(nav_buttons)

        return buttons
