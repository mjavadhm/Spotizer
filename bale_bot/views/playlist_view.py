from balethon.objects import InlineKeyboardMarkup, InlineKeyboardButton


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
                        text=playlist.name,
                        callback_data=f"playlist:add:{playlist.playlist_id}:{track_id}"
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
                    text=playlist.name,
                    callback_data=f"select_playlist:{playlist.playlist_id}"
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

    @staticmethod
    def get_playlist_details_keyboard(playlist_id, has_tracks=True):
        """Create keyboard for viewing playlist details"""
        buttons = []
        
        if has_tracks:
            buttons.append([
                InlineKeyboardButton(
                    text="📋 View Tracks",
                    callback_data=f"playlist:view_tracks:{playlist_id}"
                )
            ])
            buttons.append([
                InlineKeyboardButton(
                    text="⬇️ Download All",
                    callback_data=f"playlist:download_all:{playlist_id}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton(
                text="🗑️ Delete Playlist",
                callback_data=f"playlist:delete:{playlist_id}"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def format_playlist_tracks(playlist_name, tracks, page=1, per_page=5):
        """Format playlist tracks for display with pagination"""
        if not tracks:
            return f"🎶 *{playlist_name}*\n\nNo tracks in this playlist yet."
        
        total_tracks = len(tracks)
        total_pages = (total_tracks + per_page - 1) // per_page
        
        # Slice tracks for current page
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_tracks)
        current_tracks = tracks[start_idx:end_idx]
        
        text = f"🎶 *{playlist_name}*\n"
        text += f"Total: {total_tracks} track(s)\n\n"
        
        for idx, track in enumerate(current_tracks, start_idx + 1):
            artist_name = track.get('artist', {}).get('name', 'Unknown Artist')
            track_name = track.get('title', 'Unknown Track')
            duration = track.get('duration', 0)
            minutes = duration // 60
            seconds = duration % 60
            
            # Escape markdown special characters in names
            artist_name = artist_name.replace('*', '').replace('_', '').replace('`', '')
            track_name = track_name.replace('*', '').replace('_', '').replace('`', '')
            
            text += f"{idx}. *{track_name}* - {artist_name}\n"
            text += f"   ⏱ {minutes}:{seconds:02d}\n\n"
            
        text += f"📄 Page {page} of {total_pages}"
        
        return text

    @staticmethod
    def get_playlist_track_keyboard(tracks, playlist_id, page=1, per_page=5):
        """Create keyboard for playlist tracks with download/remove options"""
        buttons = []
        
        # Calculate pagination
        total_tracks = len(tracks)
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_tracks)
        page_tracks = tracks[start_idx:end_idx]
        
        # Add track buttons
        for track in page_tracks:
            track_name = track.get('title', 'Unknown Track')
            artist_name = track.get('artist', {}).get('name', 'Unknown Artist')
            display_name = f"{track_name} - {artist_name}"
            if len(display_name) > 40:
                display_name = display_name[:37] + "..."
            
            buttons.append([
                InlineKeyboardButton(
                    text=f"⬇️ {display_name}",
                    callback_data=f"download:track:{track['id']}"
                ),
                InlineKeyboardButton(
                    text="❌",
                    callback_data=f"playlist:remove_track:{playlist_id}:{track['playlist_track_id']}"
                )
            ])
        
        # Pagination buttons
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="◀️ Previous",
                    callback_data=f"playlist:page:{playlist_id}:{page-1}"
                )
            )
        if end_idx < total_tracks:
            nav_buttons.append(
                InlineKeyboardButton(
                    text="Next ▶️",
                    callback_data=f"playlist:page:{playlist_id}:{page+1}"
                )
            )
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        # Back button
        buttons.append([
            InlineKeyboardButton(
                text="🔙 Back to Playlists",
                callback_data="playlist:back_to_list"
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def get_download_all_keyboard(playlist_id, track_count):
        """Create keyboard for downloading all tracks from playlist"""
        buttons = [
            [
                InlineKeyboardButton(
                    text=f"✅ Confirm Download ({track_count} tracks)",
                    callback_data=f"playlist:confirm_download:{playlist_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Cancel",
                    callback_data=f"playlist:view_tracks:{playlist_id}"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def get_creation_message():
        """Message for playlist creation"""
        return "✏️ Please enter a name for your new playlist:"

    @staticmethod
    def get_creation_with_track_message():
        """Message for playlist creation when adding a track"""
        return "✏️ Please enter a name for your new playlist.\n\n💡 The selected track will be added to this playlist."
