import os
import asyncio
import logging
import requests
import models  # Import the PostgreSQL models module we created
from deezer_downloader import download_song_from_link, convert_spoty_to_dee_link_track, convert_spoty_to_dee_link_album
from spotify_utils import sp, get_spotify_item_info, Artist, playlist_creator
import view as views
import ffmpeg
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.router import Router
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.session.aiohttp import AiohttpSession
import validators
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
load_dotenv()
client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

TOKEN = os.getenv('BOT_TOKEN')

models.init_db()    

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(filename)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

API_BASE_URL = 'http://89.22.236.107:9097'
api_server = TelegramAPIServer.from_base(base=API_BASE_URL)
session = AiohttpSession(api=api_server)
bot = Bot(token=TOKEN, session=session)

dp = Dispatcher()
router = Router()

class SearchState:
    RESULTS = "search_results"
    QUERY = "search_query"
    PAGE = "current_page"
    TYPE = "search_type"

def is_url(string):
    return validators.url(string)

def get_deezer_info(content_type, deezer_id):
    url = f"https://api.deezer.com/{content_type}/{deezer_id}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"خطا در گرفتن اطلاعات از Deezer: {response.status_code}")

def get_track_list(content_type, deezer_id):
    if content_type == 'track':
        return [deezer_id]  # برای ترک تکی، فقط همون شناسه رو برمی‌گردونه
    elif content_type == 'album':
        album_info = get_deezer_info('album', deezer_id)
        return [track['id'] for track in album_info['tracks']['data']]
    elif content_type == 'playlist':
        playlist_info = get_deezer_info('playlist', deezer_id)
        return [track['id'] for track in playlist_info['tracks']['data']]
    else:
        raise ValueError(f"نوع محتوا اشتباهه: {content_type}")

def get_audio_duration(file_path):
    """ Calculate audio duration using ffmpeg """
    probe = ffmpeg.probe(file_path)
    duration = float(probe['format']['duration'])
    return int(duration)

def extract_deezer_info(url):
    """Extract content type and ID from Deezer URL"""
    # Example patterns for different Deezer URLs
    patterns = {
        'track': r'deezer\.com(?:\/[a-z]{2})?\/track\/(\d+)',
        'album': r'deezer\.com(?:\/[a-z]{2})?\/album\/(\d+)',
        'playlist': r'deezer\.com(?:\/[a-z]{2})?\/playlist\/(\d+)'
    }
    
    for content_type, pattern in patterns.items():
        match = re.search(pattern, url)
        if match:
            return content_type, int(match.group(1))
    
    return None, None

@router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    """Handle /start command and save user to database"""
    try:
        # Get all user info from Telegram
        user = message.from_user
        
        # Add user to database with all available Telegram info
        models.add_user(
            user.id, 
            user.username, 
            user.first_name, 
            user.last_name,
            is_bot=user.is_bot,
            language_code=user.language_code,
            is_premium=getattr(user, 'is_premium', False),
            added_to_attachment_menu=getattr(user, 'added_to_attachment_menu', False),
            can_join_groups=getattr(user, 'can_join_groups', True),
            can_read_all_group_messages=getattr(user, 'can_read_all_group_messages', False),
            supports_inline_queries=getattr(user, 'supports_inline_queries', False)
        )
        
        # Log the message
        models.log_message(user.id, message.text, "command")
        
        await message.reply("""🎵 Welcome to MusicDownloader Bot! 🎵

🔹 Download any track, album, or playlist effortlessly.
🔹 Get high-quality audio in your preferred format.
🔹 Option to receive albums & playlists as a ZIP file.

✨ Available Commands:

/settings – Customize your download preferences.
/history – View your recent downloads.
🎧 Simply send a link from deezer or spotify, and let the music flow! 🎧""")
    except Exception as e:
        logger.error(str(e))

@router.message(Command("settings"))
async def settings_command(message: types.Message, state: FSMContext, user_id: int = None, callback = False):
    """Handle /settings command to manage user preferences"""
    try:
        if not user_id:
            user_id = message.from_user.id
        user_settings = models.get_user_settings(user_id)
        
        if not user_settings:
            # Create default settings if not exist
            models.update_user_settings(user_id)
            user_settings = models.get_user_settings(user_id)
        
        # Create settings keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Change Quality: {user_settings['download_quality']}", 
                    callback_data="setting:change_quality"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Make ZIP: {'Yes' if user_settings['make_zip'] else 'No'}", 
                    callback_data="setting:toggle_zip"
                )
            ]
        ])
        
        # Log the message
        models.log_message(user_id, message.text, "command")
        if callback:
            await message.edit_text("⚙️ Your settings:", reply_markup=keyboard)
        else:
            await message.reply("⚙️ Your settings:", reply_markup=keyboard)
    except Exception as e:
        logger.error(str(e))
        await message.reply("Error accessing settings. Please try again later.")

@router.message(Command("history"))
async def history(message: types.Message, state: FSMContext):
    """Show user download history"""
    try:
        downloads = models.get_user_downloads(message.from_user.id, limit=5)
        
        if not downloads:
            await message.reply("You haven't downloaded any tracks yet.")
            return
        
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
        
        # Log the message
        models.log_message(message.from_user.id, message.text, "command")
        
        await message.reply(history_text)
    except Exception as e:
        logger.error(str(e))
        await message.reply("Error retrieving download history.")



async def download_deezer(user_id, link):
    print(link)
    content_type, deezer_id = extract_deezer_info(link)
    if not content_type or not deezer_id:
        await bot.send_message(chat_id=user_id, text="❌ Invalid link. Please try again.")
        return

    settings = models.get_user_settings(user_id)
    quality_download = settings.get('download_quality', 'MP3_320') if settings else 'MP3_320'
    make_zip = settings.get('make_zip', True) if settings else True
    if content_type != 'track' and make_zip:
        existing_zip = models.get_user_download_by_deezer_id(user_id, deezer_id, quality=quality_download)
        if existing_zip:
            await bot.send_document(
                chat_id=user_id,
                document=existing_zip['file_id'],
                caption=f"@Spotizer_bot 🎧"
            )
            return
        smart = download_song_from_link(link, quality_download=quality_download, make_zip=make_zip)
        if smart.album:
            file_path = smart.album.zip_path
            document = FSInputFile(file_path)
            sent_message = await bot.send_document(
                chat_id=user_id, 
                document=document, 
                caption=f"@Spotizer_bot 🎧"
            )
            
            models.add_user_download(
                    user_id=user_id,
                    deezer_id=deezer_id,
                    content_type='album',
                    file_id=sent_message.document.file_id,
                    quality=quality_download,
                    url=link,
                    title=smart.album.title,
                    artist=smart.album.artist
                )
            print(str(smart.album.title))
            # os.remove(file_path)
            logger.info(f"File {file_path} has been deleted.")
            
        elif smart.playlist:
            file_path = smart.playlist.zip_path
            document = FSInputFile(file_path)
            sent_message = await bot.send_document(
                chat_id=user_id, 
                document=document, 
                caption=f"@Spotizer_bot 🎧"
            )
            
            models.add_user_download(
                    user_id=user_id,
                    deezer_id=deezer_id,
                    content_type='playlist',
                    file_id=sent_message.document.file_id,
                    quality=quality_download,
                    url=link,
                    title=smart.playlist.title,
                    artist=smart.playlist.artist
                )
            
            os.remove(file_path)
            logger.info(f"File {file_path} has been deleted.")
        
    # گرفتن لیست ترک‌ها
    else:
        track_ids = get_track_list(content_type, deezer_id)
        musics_playlist = []
        # برای هر ترک
        for track_id in track_ids:
            # چک کردن دیتابیس
            existing_track = models.get_user_download_by_deezer_id(user_id, track_id, 'track', quality_download)
            if existing_track:
                await bot.send_audio(
                    chat_id=user_id,
                    audio=existing_track['file_id'],
                    caption=f"@Spotizer_bot 🎧",
                    title=existing_track['title'],
                    performer=existing_track['artist']
                )
                musics = (existing_track['title'], existing_track['duration'], existing_track['file_name'])
                musics_playlist.append(musics)
            else:
                track_link = f"https://www.deezer.com/track/{track_id}"
                smart = download_song_from_link(track_link, quality_download=quality_download, make_zip=False)
                if smart.track:
                    file_path = smart.track.song_path
                    audio_file = FSInputFile(file_path)
                    duration = get_audio_duration(file_path)
                    
                    if hasattr(smart.track, 'music'):
                        title = smart.track.music
                        logger.info(f"Title music: {title}")
                        
                    else:
                        logger.error(f"Title not found for track {track_id}")
                        try:
                            logger.info(f"Track info: {smart.track}")
                            logger.info(f"Track info: {str(smart.track)}")
                        finally:
                            title = f"Track {track_id}"
                    
                    if hasattr(smart.track, 'artist'):
                        artist = smart.track.artist
                    else:
                        logger.error(f"Artist not found for track {track_id}")
                        try:
                            logger.info(f"Track info: {smart.track}")
                            logger.info(f"Track info: {str(smart.track)}")
                        finally:
                            artist = "Unknown Artist"

                    sent_message = await bot.send_audio(
                        chat_id=user_id,
                        audio=audio_file,
                        caption=f"@Spotizer_bot 🎧",
                        duration=duration,
                        title=title,
                        performer=artist
                    )
                    models.add_user_download(
                        user_id=user_id,
                        deezer_id=track_id,
                        content_type='track',
                        file_id=sent_message.audio.file_id,
                        quality=quality_download,
                        url=track_link,
                        title=title,
                        artist=artist,
                        duration=duration,
                        file_name=sent_message.audio.file_name
                    )
                    musics = (title, duration, sent_message.audio.file_name)
                    musics_playlist.append(musics)
                    os.remove(file_path)
        await playlist_creator(musics_playlist, "playlist.m3u")
        await bot.send_document(
            chat_id=user_id,
            document=FSInputFile("playlist.m3u"),
            caption=f"@Spotizer_bot 🎧"
        )
        os.remove("playlist.m3u")
        logger.info(f"File playlist.m3u has been deleted.")


@router.message(F.text)
async def process_link(message: types.Message, state: FSMContext):
    """Process music link and download if valid"""
    try:
        user_input = message.text
        chat_id = message.chat.id
        user_id = message.from_user.id
        if is_url(user_input):
            url = user_input
            logger.info(f"Received URL: {url} from chat {chat_id}")
            
            # Log the received message
            models.log_message(chat_id, url, "link")
            
            if "spotify" in url:
                if 'playlist' in url:
                    await message.reply("Spotify playlists are not supported yet. Please use a Deezer link.")
                    return
                if 'album' in url:
                    url = convert_spoty_to_dee_link_album(url)
                else:
                    url = convert_spoty_to_dee_link_track(url)
            elif 'deezer' not in url:
                await message.reply("❌ Invalid link. Please try again.")
                return

            # Send processing message
            status_message = await message.reply("⏳")
            
            # Start download process
            await download_deezer(chat_id, url)
            
            # Update status message
            await status_message.delete()
        else:
            query = user_input
            await state.update_data({SearchState.QUERY: query, SearchState.PAGE: 0})
    
            # Create keyboard with search options
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Search Tracks", callback_data=f"search:track:{query}"),
                    InlineKeyboardButton(text="Search Albums", callback_data=f"search:album:{query}")
                ],
                [
                    InlineKeyboardButton(text="Search Playlists", callback_data=f"search:playlist:{query}")
                ]
            ])
            
            await message.reply(f"What do you want to search for '{query}'?", reply_markup=keyboard)
    except Exception as e:
        logger.error(str(e))
        await message.reply("Error processing your link. Please try again or use a different link.")

# Register callbacks for settings buttons
@router.callback_query()
async def callback_query_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    settings = models.get_user_settings(user_id)
    raw_callback_data = callback_query.data
    if raw_callback_data == "delete":
        await callback_query.message.delete()
        return
    callback_data = raw_callback_data.split(":")
    if callback_data[0] == "setting":
        if callback_data[1] == "change_quality":
            await change_quality(callback_query, state)
        elif callback_data[1] == "toggle_zip":
            await toggle_zip(callback_query, state)
    elif callback_data[0] == "set_quality":
        quality = callback_data[1]
        if quality == "back":
            await callback_query.answer("Back to settings")
            await settings_command(callback_query.message, state, user_id, True)
            return
        await change_quality(callback_query, state, quality)
    elif callback_data[0] == "search":
        await search_callback_handler(callback_query, state)
    elif callback_data[0] == "page":
        page = int(callback_data[1])
        search_type = callback_data[2]
        query = callback_data[3]
        await perform_search(callback_query, state, query, search_type, page)
    elif callback_data[0] == "select":
        await select_callback_handler(callback_query, state, callback_data, user_id)
    elif callback_data[0] == "view":
        await view_handler(callback_query, state, callback_data, user_id)
    elif callback_data[0] == "download":
        await download_deezer_by_callback(callback_query, state, callback_data, user_id)

async def select_callback_handler(callback_query: types.CallbackQuery, state: FSMContext, callback_data, user_id):
    try:
        content_type = callback_data[1]
        spo_id = callback_data[2]
        message = callback_query.message
        if content_type == 'track':
            await views.select_track(message, state, spo_id, user_id)    
        elif content_type == 'album':
            await views.select_album(message, state, spo_id, user_id)
        elif content_type == 'playlist':
            await views.select_playlist(message, state, spo_id, user_id)
        elif content_type == 'artist':
            await views.select_artist(message, state, spo_id, user_id)
            
    except Exception as e:
        logger.error(str(e))
        await callback_query.answer("Error getting item info. Please try again later.")

# Handler for viewing album/playlist tracks
async def view_handler(callback_query: types.CallbackQuery, state: FSMContext, callback_data, user_id=None):
    try:
        if not user_id:
            user_id = callback_query.from_user.id
            
        # Check length of callback_data to determine format
        # Format should be: ["view", content_type, "tracks", item_id, optional_page]
        if len(callback_data) < 4:
            logger.error(f"Invalid callback data format: {callback_data}")
            await callback_query.answer("Invalid callback data. Please try again.")
            return
            
        view_type = callback_data[0]  # Should be "view"
        content_type = callback_data[1]  # "album" or "playlist" or "artist"
        action = callback_data[2]  # "tracks", "top_tracks", "albums", "related"
        item_id = callback_data[3]  # Spotify ID
        
        # Check if there's a page number in the callback data
        page = 1
        if len(callback_data) > 4:
            try:
                page = int(callback_data[4])
            except ValueError:
                page = 1
        
        # Items per page
        items_per_page = 8
        
        if content_type == "album":
            try:
                album = get_spotify_item_info('album', item_id)
                if album:
                    tracks = album['tracks']
                    total_pages = (len(tracks) + items_per_page - 1) // items_per_page
                    
                    # Get tracks for current page
                    start_idx = (page - 1) * items_per_page
                    end_idx = min(start_idx + items_per_page, len(tracks))
                    current_page_tracks = tracks[start_idx:end_idx]
                    
                    # Create buttons for current page tracks
                    tracks_buttons = []
                    for track in current_page_tracks:
                        tracks_buttons.append([
                            InlineKeyboardButton(
                                text=f"{track['track_number']}. {track['name']} ({track['duration']})", 
                                callback_data=f"select:track:{track['id']}"
                            )
                        ])
                    
                    # Add navigation buttons
                    nav_buttons = []
                    if page > 1:
                        nav_buttons.append(InlineKeyboardButton(
                            text="⬅️ Previous", 
                            callback_data=f"view:album:tracks:{item_id}:{page-1}"
                        ))
                    
                    nav_buttons.append(InlineKeyboardButton(
                        text=f"📄 {page}/{total_pages}", 
                        callback_data=f"page_info"
                    ))
                    
                    if page < total_pages:
                        nav_buttons.append(InlineKeyboardButton(
                            text="Next ➡️", 
                            callback_data=f"view:album:tracks:{item_id}:{page+1}"
                        ))
                    
                    tracks_buttons.append(nav_buttons)
                    
                    # Add back button 
                    tracks_buttons.append([InlineKeyboardButton(
                        text="⬅️ Back to Album", 
                        callback_data=f"select:album:{item_id}"
                    )])
                    
                    # Add delete button
                    tracks_buttons.append([InlineKeyboardButton(
                        text="❌ Close", 
                        callback_data="delete"
                    )])
                    
                    await callback_query.message.edit_caption(
                        caption=f"*Tracks in album '{album['name']}' by {album['main_artist']}:*\n*Page {page}/{total_pages}*",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=tracks_buttons)
                    )
                    return
            except Exception as e:
                logger.error(f"Error in album view: {str(e)}")
                await callback_query.answer("Error retrieving album tracks. Please try again.")
                
        elif content_type == "playlist":
            try:
                playlist = get_spotify_item_info('playlist', item_id)
                if playlist:
                    tracks = playlist['tracks']
                    total_pages = (len(tracks) + items_per_page - 1) // items_per_page
                    
                    # Get tracks for current page
                    start_idx = (page - 1) * items_per_page
                    end_idx = min(start_idx + items_per_page, len(tracks))
                    current_page_tracks = tracks[start_idx:end_idx]
                    
                    # Create buttons for current page tracks
                    tracks_buttons = []
                    for i, track in enumerate(current_page_tracks, start_idx + 1):
                        tracks_buttons.append([
                            InlineKeyboardButton(
                                text=f"{i}. {track['name']} - {track['main_artist']} ({track['duration']})", 
                                callback_data=f"select:track:{track['id']}"
                            )
                        ])
                    
                    # Add navigation buttons
                    nav_buttons = []
                    if page > 1:
                        nav_buttons.append(InlineKeyboardButton(
                            text="⬅️ Previous", 
                            callback_data=f"view:playlist:tracks:{item_id}:{page-1}"
                        ))
                    
                    nav_buttons.append(InlineKeyboardButton(
                        text=f"📄 {page}/{total_pages}", 
                        callback_data=f"page_info"
                    ))
                    
                    if page < total_pages:
                        nav_buttons.append(InlineKeyboardButton(
                            text="Next ➡️", 
                            callback_data=f"view:playlist:tracks:{item_id}:{page+1}"
                        ))
                    
                    tracks_buttons.append(nav_buttons)
                    
                    # Add back button 
                    tracks_buttons.append([InlineKeyboardButton(
                        text="⬅️ Back to Playlist", 
                        callback_data=f"select:playlist:{item_id}"
                    )])
                    
                    # Add delete button
                    tracks_buttons.append([InlineKeyboardButton(
                        text="❌ Close", 
                        callback_data="delete"
                    )])
                    
                    # Note about more tracks if applicable
                    more_tracks_note = ""
                    if playlist.get('more_tracks_available', False):
                        more_tracks_note = f"\n*Note: Only showing {playlist['tracks_fetched']} of {playlist['total_tracks']} tracks*"
                    
                    await callback_query.message.edit_caption(
                        caption=f"*Tracks in playlist '{playlist['name']}':*\n*Page {page}/{total_pages}*{more_tracks_note}",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=tracks_buttons)
                    )
                    return
            except Exception as e:
                logger.error(f"Error in playlist view: {str(e)}")
                await callback_query.answer("Error retrieving playlist tracks. Please try again.")
                
        elif content_type == "artist":
            try:
                artist = Artist(item_id)
                
                if action == "top_tracks":
                    # Display top tracks
                    top_tracks = artist.top_tracks
                    total_pages = (len(top_tracks) + items_per_page - 1) // items_per_page
                    
                    # Get tracks for current page
                    start_idx = (page - 1) * items_per_page
                    end_idx = min(start_idx + items_per_page, len(top_tracks))
                    current_page_tracks = top_tracks[start_idx:end_idx]
                    
                    # Create buttons for current page tracks
                    tracks_buttons = []
                    for i, track in enumerate(current_page_tracks, start_idx + 1):
                        tracks_buttons.append([
                            InlineKeyboardButton(
                                text=f"{i}. {track['name']} ({track.get('duration', 'N/A')})", 
                                callback_data=f"select:track:{track['id']}"
                            )
                        ])
                    
                    # Add navigation buttons if needed
                    nav_buttons = []
                    if page > 1:
                        nav_buttons.append(InlineKeyboardButton(
                            text="⬅️ Previous", 
                            callback_data=f"view:artist:top_tracks:{item_id}:{page-1}"
                        ))
                    
                    nav_buttons.append(InlineKeyboardButton(
                        text=f"📄 {page}/{total_pages}", 
                        callback_data=f"page_info"
                    ))
                    
                    if page < total_pages:
                        nav_buttons.append(InlineKeyboardButton(
                            text="Next ➡️", 
                            callback_data=f"view:artist:top_tracks:{item_id}:{page+1}"
                        ))
                    
                    if nav_buttons:
                        tracks_buttons.append(nav_buttons)
                    
                    # Add back button 
                    tracks_buttons.append([InlineKeyboardButton(
                        text="⬅️ Back to Artist", 
                        callback_data=f"select:artist:{item_id}"
                    )])
                    
                    # Add delete button
                    tracks_buttons.append([InlineKeyboardButton(
                        text="❌ Close", 
                        callback_data="delete"
                    )])
                    
                    await callback_query.message.edit_caption(
                        caption=f"*Top tracks by {artist.artist_name}:*\n*Page {page}/{total_pages}*",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=tracks_buttons)
                    )
                    return
                
                elif action == "albums":
                    # Display albums
                    albums = artist.albums
                    total_pages = (len(albums) + items_per_page - 1) // items_per_page
                    
                    # Get albums for current page
                    start_idx = (page - 1) * items_per_page
                    end_idx = min(start_idx + items_per_page, len(albums))
                    current_page_albums = albums[start_idx:end_idx]
                    
                    # Create buttons for current page albums
                    album_buttons = []
                    for i, album in enumerate(current_page_albums, start_idx + 1):
                        album_buttons.append([
                            InlineKeyboardButton(
                                text=f"{i}. {album['name']} ({album.get('release_date', 'N/A')})", 
                                callback_data=f"select:album:{album['id']}"
                            )
                        ])
                    
                    # Add navigation buttons if needed
                    nav_buttons = []
                    if page > 1:
                        nav_buttons.append(InlineKeyboardButton(
                            text="⬅️ Previous", 
                            callback_data=f"view:artist:albums:{item_id}:{page-1}"
                        ))
                    
                    nav_buttons.append(InlineKeyboardButton(
                        text=f"📄 {page}/{total_pages}", 
                        callback_data=f"page_info"
                    ))
                    
                    if page < total_pages:
                        nav_buttons.append(InlineKeyboardButton(
                            text="Next ➡️", 
                            callback_data=f"view:artist:albums:{item_id}:{page+1}"
                        ))
                    
                    if nav_buttons:
                        album_buttons.append(nav_buttons)
                    
                    # Add back button 
                    album_buttons.append([InlineKeyboardButton(
                        text="⬅️ Back to Artist", 
                        callback_data=f"select:artist:{item_id}"
                    )])
                    
                    # Add delete button
                    album_buttons.append([InlineKeyboardButton(
                        text="❌ Close", 
                        callback_data="delete"
                    )])
                    
                    # Note about limited albums if applicable
                    albums_note = ""
                    if len(artist.albums) == 5:
                        albums_note = "\n*Note: Only showing top 5 albums*"
                    
                    await callback_query.message.edit_caption(
                        caption=f"*Albums by {artist.artist_name}:*\n*Page {page}/{total_pages}*{albums_note}",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=album_buttons)
                    )
                    return
                
                elif action == "related":
                    # Display related artists
                    related_artists = artist.related_artists
                    total_pages = (len(related_artists) + items_per_page - 1) // items_per_page
                    
                    # Get related artists for current page
                    start_idx = (page - 1) * items_per_page
                    end_idx = min(start_idx + items_per_page, len(related_artists))
                    current_page_artists = related_artists[start_idx:end_idx]
                    
                    # Create buttons for current page related artists
                    artist_buttons = []
                    for i, related in enumerate(current_page_artists, start_idx + 1):
                        artist_buttons.append([
                            InlineKeyboardButton(
                                text=f"{i}. {related['name']}", 
                                callback_data=f"select:artist:{related['id']}"
                            )
                        ])
                    
                    # Add navigation buttons if needed
                    nav_buttons = []
                    if page > 1:
                        nav_buttons.append(InlineKeyboardButton(
                            text="⬅️ Previous", 
                            callback_data=f"view:artist:related:{item_id}:{page-1}"
                        ))
                    
                    nav_buttons.append(InlineKeyboardButton(
                        text=f"📄 {page}/{total_pages}", 
                        callback_data=f"page_info"
                    ))
                    
                    if page < total_pages:
                        nav_buttons.append(InlineKeyboardButton(
                            text="Next ➡️", 
                            callback_data=f"view:artist:related:{item_id}:{page+1}"
                        ))
                    
                    if nav_buttons:
                        artist_buttons.append(nav_buttons)
                    
                    # Add back button 
                    artist_buttons.append([InlineKeyboardButton(
                        text="⬅️ Back to Artist", 
                        callback_data=f"select:artist:{item_id}"
                    )])
                    
                    # Add delete button
                    artist_buttons.append([InlineKeyboardButton(
                        text="❌ Close", 
                        callback_data="delete"
                    )])
                    
                    await callback_query.message.edit_caption(
                        caption=f"*Artists related to {artist.artist_name}:*\n*Page {page}/{total_pages}*",
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=artist_buttons)
                    )
                    return
            except Exception as e:
                logger.error(f"Error in artist view: {str(e)}")
                await callback_query.answer("Error retrieving artist information. Please try again.")
        
        else:
            logger.error(f"Unknown content type: {content_type}")
            await callback_query.answer("Unknown content type. Please try again.")
            
    except Exception as e:
        logger.error(f"View handler error: {str(e)}")
        await callback_query.answer("Error getting item info. Please try again later.")

async def download_deezer_by_callback(callback_query: types.CallbackQuery, state: FSMContext, callback_data, user_id):
    try:
        status_message = await callback_query.message.reply("⏳")
        content_type = callback_data[1]
        spotify_id = callback_data[2]
        url = f"https://open.spotify.com/{content_type}/{spotify_id}"
        if 'playlist' in url:
            await callback_query.reply("Spotify playlists are not supported yet. Please use a Deezer link.")
            return
        if 'album' in url:
            url = convert_spoty_to_dee_link_album(url)
        else:
            url = convert_spoty_to_dee_link_track(url)
        await download_deezer(user_id, url)
        await status_message.delete()
    except Exception as e:
        logger.error(str(e))
        await callback_query.answer("Error downloading from Spotify. Please try again later.")
async def change_quality(callback_query: types.CallbackQuery, state: FSMContext, set=None):
    try:
        user_id = callback_query.from_user.id
        if set:
            models.update_user_settings(user_id, download_quality=set)
            await callback_query.answer(f"Quality set to {set}")
            
        settings = models.get_user_settings(user_id)
        quality_options = ["MP3_128", "MP3_320", "FLAC"]
        
        buttons = []
        for option in quality_options:
            text = option
            if option == settings['download_quality']:
                text += " ✅"
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"set_quality:{option}")])
        
        # Add the "Back" button
        buttons.append([InlineKeyboardButton(text="Back", callback_data="set_quality:back")])

        # Create the keyboard correctly
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback_query.message.edit_reply_markup(reply_markup=keyboard)
        await callback_query.answer("Select your preferred quality:")
    except Exception as e:
        logger.error(str(e))
        await callback_query.answer("Error changing quality. Please try again later.")

async def toggle_zip(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    settings = models.get_user_settings(user_id)
    
    # Toggle zip setting
    new_zip_setting = not settings['make_zip']
    
    # Update settings
    models.update_user_settings(user_id, make_zip=new_zip_setting)
    
    # Update inline keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Change Quality: {settings['download_quality']}Quality",
                    callback_data="setting:change_quality"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Make ZIP: {'Yes' if new_zip_setting else 'No'}", 
                    callback_data="setting:toggle_zip"
                )
            ]
        ])
    
    await callback_query.message.edit_reply_markup(reply_markup=keyboard)
    await callback_query.answer(f"ZIP mode {'enabled' if new_zip_setting else 'disabled'}")

async def search_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        # Extract data from callback
        user_id = callback_query.from_user.id
        data = callback_query.data.split(":")
        search_type = data[1]  # track, album, playlist
        
        # Get query from state or callback data
        if len(data) > 2:
            query = data[2]
            await state.update_data({
                SearchState.QUERY: query, 
                SearchState.TYPE: search_type,
                SearchState.PAGE: 0
            })
        else:
            state_data = await state.get_data()
            query = state_data.get(SearchState.QUERY)
            
        if not query:
            await callback_query.answer("No search term found. Please try again.")
            return
            
        # Perform search based on type
        await perform_search(callback_query, state, query, search_type)
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        await callback_query.answer("Error performing search. Please try again later.")

async def perform_search(callback_query: types.CallbackQuery, state: FSMContext, query: str, search_type: str, page=0):
    """Perform search on Spotify and display results with pagination"""
    try:
        # Get current page
        offset = page * 5
        
        # Search on Spotify
        if search_type == "track":
            results = sp.search(q=query, type="track", limit=5, offset=offset)
            items = results['tracks']['items']
            total = results['tracks']['total']
        elif search_type == "album":
            results = sp.search(q=query, type="album", limit=5, offset=offset)
            items = results['albums']['items']
            total = results['albums']['total']
        elif search_type == "playlist":
            results = sp.search(q=query, type="playlist", limit=5, offset=offset)
            items = results['playlists']['items']
            total = results['playlists']['total']
        else:
            await callback_query.answer("Invalid search type")
            return
            
        # Save results to state
        await state.update_data({SearchState.RESULTS: items})
        
        # Check if we have results
        if not items:
            await callback_query.answer("No results found")
            await callback_query.message.edit_text(
                f"No {search_type}s found for '{query}'", 
                reply_markup=None
            )
            return
            
        # Create keyboard with results
        buttons = []
        for i, item in enumerate(items):
            # Format display text based on item type
            if search_type == "track":
                artists = ", ".join([artist['name'] for artist in item['artists']])
                text = f"🎵 {item['name']} - {artists}"
            elif search_type == "album":
                artists = ", ".join([artist['name'] for artist in item['artists']])
                text = f"📀 {item['name']} by {artists}"
            else:  # playlist
                text = f"📑 {item['name']} ({item['tracks']['total']} tracks)"
                
            # Truncate long titles
            if len(text) > 60:
                text = text[:57] + "..."
                
            # Create button with callback data in the specified format
            buttons.append([
                InlineKeyboardButton(
                    text=text, 
                    callback_data=f"select:{search_type}:{item['id']}"
                )
            ])
        
        # Add navigation buttons
        nav_buttons = []
        
        # Add prev button if not on first page
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"page:{page-1}:{search_type}:{query}"))
            
        # Add next button if there are more results
        if offset + 10 < total:
            nav_buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"page:{page+1}:{search_type}:{query}"))
            
        if nav_buttons:
            buttons.append(nav_buttons)
            
        
        buttons.append([
            InlineKeyboardButton(text="❌", callback_data=f"delete")
        ])
        
        # Create the keyboard
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Update message with results
        result_type_name = search_type.capitalize() + "s"
        await callback_query.message.edit_text(
            f"Search results for '{query}' ({result_type_name}):\n"
            f"Page {page + 1} of {(total + 9) // 10}",
            reply_markup=keyboard
        )
        
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        await callback_query.answer("Error performing search. Please try again later.")

dp.include_router(router)

async def main():
    # Initialize database on startup
    models.init_db()
    logger.info("Database initialized")
    
    # Start the bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())