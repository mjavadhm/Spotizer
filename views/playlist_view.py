from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class PlaylistView:
    @staticmethod
    def get_playlist_for_add_keyboard(playlists, track_id):
        """Create playlist selection keyboard markup"""
        buttons = []
        buttons.append([
            InlineKeyboardButton(
                text="New Playlist",
                callback_data=f"playlist:new_and_add:{track_id}"
            )
        ])
        if playlists:
            for playlist in playlists:
                buttons.append([
                    InlineKeyboardButton(
                        text=playlist['name'],
                        callback_data=f"select_playlist:add:{playlist['id']}:{track_id}"
                    )
                ])

            text = "Choose a playlist to add"
        else:
            text = "No playlists available please create one"
        return InlineKeyboardMarkup(inline_keyboard=buttons), text

    
    @staticmethod
    def get_playlist_keyboard(playlists):
        """Create playlist selection keyboard markup"""
        buttons = []
        for playlist in playlists:
            buttons.append([
                InlineKeyboardButton(
                    text=playlist['name'],
                    callback_data=f"select_playlist:{playlist['id']}"
                )
            ])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def get_choose_playlist_message():
        """select playlist"""
        text = "🎶 Choose a playlist"
        return text

    @staticmethod
    def get_quality_options_keyboard(current_quality):
        """Create quality options keyboard markup"""
        quality_options = ["MP3_128", "MP3_320", "FLAC"]
        buttons = []
        
        for option in quality_options:
            text = f"{option} {'✅' if option == current_quality else ''}"
            buttons.append([
                InlineKeyboardButton(text=text, callback_data=f"set_quality:{option}")
            ])
        
        buttons.append([
            InlineKeyboardButton(text="Back", callback_data="set_quality:back")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def format_download_history(downloads):
        """Format download history message"""
        if not downloads:
            return "You haven't downloaded any tracks yet."

        history_text = "Your recent downloads:\n\n"
        for i, download in enumerate(downloads, 1):
            track_info = f"{i}. "
            
            if download['title'] and download['artist']:
                track_info += f"{download['title']} - {download['artist']}"
            else:
                track_info += f"{download['content_type'].capitalize()} #{download['deezer_id']}"
            
            track_info += f"\n   🎭 Type: {download['content_type'].capitalize()}"
            track_info += f"\n   🔊 Quality: {download['quality']}"
            track_info += f"\n   📅 {download['downloaded_at'].strftime('%Y-%m-%d %H:%M')}"
            history_text += track_info + "\n\n"
            
        return history_text

    @staticmethod
    def get_error_message(error_type):
        """Return formatted error messages"""
        error_messages = {
            'invalid_url': "❌ Invalid link. Please provide a valid Deezer or Spotify link.",
            'download_failed': "❌ Download failed. Please try again or use a different link.",
            'spotify_playlist': "Spotify playlists are not supported yet. Please use a Deezer link.",
            'settings_error': "Error accessing settings. Please try again later.",
            'history_error': "Error retrieving download history.",
            'general_error': "An error occurred. Please try again later."
        }
        return error_messages.get(error_type, error_messages['general_error'])

    @staticmethod
    def get_search_keyboard(query):
        """Create search options keyboard markup"""
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Search Tracks", callback_data=f"search:track:{query}"),
                InlineKeyboardButton(text="Search Albums", callback_data=f"search:album:{query}")
            ],
            [
                InlineKeyboardButton(text="Search Playlists", callback_data=f"search:playlist:{query}"),
                InlineKeyboardButton(text="Search Artist", callback_data=f"search:artist:{query}")
            ]
            
        ])
        return keyboard
