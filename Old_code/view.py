from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.router import Router
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.session.aiohttp import AiohttpSession
from spotify_utils import get_spotify_item_info, Artist

async def select_track(message: types.Message, state: FSMContext, spo_id, user_id):
    try:
            track = get_spotify_item_info('track', spo_id)
            
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
            
            buttons = []
            buttons.append([InlineKeyboardButton(text="📥 Download", callback_data=f"download:track:{spo_id}")])
            buttons.append([InlineKeyboardButton(text="🎨 Artist", callback_data=f"select:artist:{track['artists'][0]['id']}")])
            buttons.append([InlineKeyboardButton(text="📀 Album", callback_data=f"select:album:{track['album']['id']}")])
            buttons.append([InlineKeyboardButton(text="❌", callback_data="delete")])
            
            await message.reply_photo(
                photo=track['thumbnail'],
                caption=text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
            
    except Exception as e:
        raise e
    
async def select_album(message: types.Message, state: FSMContext, spo_id, user_id):
    try:
            album = get_spotify_item_info('album', spo_id)
            
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
            
            buttons = []
            buttons.append([InlineKeyboardButton(text="📥 Download Album", callback_data=f"download:album:{spo_id}")])
            buttons.append([InlineKeyboardButton(text=f"🎨 Artist:{album['main_artist']}", callback_data=f"select:artist:{album['artists'][0]['id']}")])
            # Updated callback format to include "tracks"
            buttons.append([InlineKeyboardButton(text="🎵 View Tracks", callback_data=f"view:album:tracks:{spo_id}:1")])
            buttons.append([InlineKeyboardButton(text="❌", callback_data="delete")])
            
            await message.reply_photo(
                photo=album['thumbnail'],
                caption=text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
    except Exception as e:
        raise e

async def select_artist(message: types.Message, state: FSMContext, spo_id, user_id):
    try:
            artist = Artist(spo_id)
            
            # Format genres list
            genres_text = ""
            if artist.artist_genres:
                genres_text = ", ".join(artist.artist_genres[:3])
                if len(artist.artist_genres) > 3:
                    genres_text += f" and {len(artist.artist_genres) - 3} more"
            else:
                genres_text = "Not available"
            
            # Format text
            text = f"""🎨 *Artist:* [{artist.artist_name}]({artist.artist_url})

👥 *Followers:* {artist.artist_followers:,}

🔥 *Popularity:* {artist.artist_popularity}/100

🎭 *Genres:* {genres_text}
"""
            
            buttons = []
            # Add top tracks button
            buttons.append([InlineKeyboardButton(text="🔝 Top Tracks", callback_data=f"view:artist:top_tracks:{spo_id}:1")])
            # Add albums button
            buttons.append([InlineKeyboardButton(text="💿 Albums", callback_data=f"view:artist:albums:{spo_id}:1")])
            # Add related artists if available
            if artist.related_artists:
                buttons.append([InlineKeyboardButton(text="👥 Related Artists", callback_data=f"view:artist:related:{spo_id}:1")])
            buttons.append([InlineKeyboardButton(text="❌", callback_data="delete")])
            
            await message.reply_photo(
                photo=artist.artist_thumbnail,
                caption=text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
    except Exception as e:
        raise e

async def select_playlist(message: types.Message, state: FSMContext, spo_id, user_id):
    try:
            playlist = get_spotify_item_info('playlist', spo_id)
            
            # Format tracks list (shortened)
            
            text = f"""📑 *Playlist:* [{playlist['name']}]({playlist['url']})

👤 *Creator:* {playlist['owner']['name']}

ℹ️ *Description:* {playlist['description']}

🎵 *Tracks:* {playlist['total_tracks']}
"""
            
            buttons = []
            # Updated callback format to include "tracks"
            buttons.append([InlineKeyboardButton(text="🎵 View Tracks", callback_data=f"view:playlist:tracks:{spo_id}:1")])
            buttons.append([InlineKeyboardButton(text="📥 Download Playlist", callback_data=f"download:playlist:{spo_id}")])
            buttons.append([InlineKeyboardButton(text="❌", callback_data="delete")])
            
            await message.reply_photo(
                photo=playlist['thumbnail'],
                caption=text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
    except Exception as e:
        raise e