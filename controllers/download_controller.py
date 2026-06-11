import aiogram
import os
from sqlalchemy.future import select
from sqlalchemy.sql import func
from database.session import async_session_maker
from controllers.user_controller import UserController
from models.base import User, UserSettings, UserDownload, Track
from services.yt_dlp_service import YTDlpService
from services.ytmusic_service import YTMusicService
from utils.file_handler import FileHandler
from utils.url_validator import URLValidator
from views.music_view import MusicView
from aiogram.types import FSInputFile
from bot import bot
from logger import get_logger

logger = get_logger(__name__)

class DownloadController:
    def __init__(self):
        self.yt_dlp_service = YTDlpService()
        self.ytmusic_service = YTMusicService()
        self.file_handler = FileHandler()
        self.url_validator = URLValidator()
        logger.info("DownloadController initialized")

    @staticmethod
    async def add_download(user_id, yt_id, content_type, file_id, quality, url, title, artist, album, duration=None, file_name=None, channel_id=None, message_id=None):
        """Add a download to the database."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserDownload).where(
                    UserDownload.user_id == user_id,
                    UserDownload.yt_id == yt_id,
                    UserDownload.content_type == content_type,
                    UserDownload.quality == quality
                )
            )
            existing = result.scalars().first()
            
            if existing:
                existing.downloaded_at = func.now()
                existing.file_id = file_id
                await session.commit()
                return existing.download_id
            
            download = UserDownload(
                user_id=user_id,
                yt_id=yt_id,
                content_type=content_type,
                file_id=file_id,
                quality=quality,
                url=url,
                title=title,
                artist=artist,
                album=album,
                duration=duration,
                file_name=file_name,
            )
            session.add(download)
            await session.commit()
            await session.refresh(download)
            return download.download_id

    @staticmethod
    async def get_track(track_id):
        async with async_session_maker() as session:
            return await session.get(Track, track_id)

    @staticmethod
    async def add_track(track_id, url, file_id, title, artist, album, duration, quality, channel_id=None, message_id=None, spotify_id=None):
        async with async_session_maker() as session:
            async with session.begin():
                track = Track(
                    track_id=track_id,
                    spotify_id=spotify_id,
                    url=url,
                    file_id=file_id,
                    title=title,
                    artist=artist,
                    album=album,
                    duration=duration,
                    quality=quality,
                    channel_id=channel_id,
                    message_id=message_id,
                )
                session.add(track)
            await session.commit()

    async def search(self, query: str, search_type: str, page: int = 1) -> tuple[bool, list]:
        try:
            logger.info(f"Searching for {search_type}s with query: {query} (Page: {page})")
            offset = (page - 1) * 5
            limit = offset + 5
            results = await self.ytmusic_service.search(query, search_type, limit=limit, offset=0)
            
            page_results = results[offset:offset+5]
            if page_results:
                return True, page_results
            else:
                return False, []
        except Exception as e:
            logger.error(f"Search error for {search_type}s - Query: {query}: {str(e)}", exc_info=True)
            return False, []

    async def get_item_info(self, content_type: str, item_id: str) -> tuple[bool, dict]:
        try:
            logger.info(f"Getting info for {content_type} with ID: {item_id}")
            item_info = await self.ytmusic_service.get_item_info(content_type, item_id)
            if item_info:
                return True, item_info
            else:
                return False, {}
        except Exception as e:
            logger.error(f"Error getting item info for {content_type} {item_id}: {str(e)}", exc_info=True)
            return False, {}

    @staticmethod
    async def get_track_by_yt_id_quality(user_id, yt_id, quality):
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserDownload)
                .where(
                    UserDownload.user_id == user_id,
                    UserDownload.yt_id == yt_id,
                    UserDownload.quality == quality,
                )
            )
            return result.scalars().first()

    async def process_download_request(self, user_id, url):
        try:
            logger.info(f"Processing download request for user {user_id} - URL: {url}")
            
            if not self.url_validator.is_ytmusic_url(url):
                logger.error(f"Invalid URL format provided by user {user_id}: {url}")
                return False, "Invalid URL format. Please provide a valid YouTube Music link."

            success, user_settings = await UserController.get_user_settings(user_id)
            if not success:
                quality = 'MP3_320'
                make_zip = True
            else:
                quality = user_settings.get('download_quality', 'MP3_320')
                make_zip = user_settings.get('make_zip', True)
                
            content_type, yt_id = self.url_validator.extract_ytmusic_info(url)
            
            if not content_type or not yt_id:
                logger.error(f"Could not extract content type or ID from URL: {url}")
                return False, "❌ Invalid URL format. Please provide a valid YouTube Music link."

            if make_zip and content_type != 'track':
                existing_zip = await self.get_track_by_yt_id_quality(user_id, yt_id, quality)
                if existing_zip:
                    await bot.send_document(
                        chat_id=user_id,
                        document=existing_zip.file_id,
                        caption=f"@Spotizer_bot 🎧"
                    )
                    return True, "Sent existing ZIP file"

                smart = await self.yt_dlp_service.download(url, quality_download=quality, make_zip=True)
                
                collection = smart.album if smart.album else smart.playlist
                if collection:
                    file_path = collection.zip_path
                    document = FSInputFile(file_path)
                    
                    music_channel_id = os.getenv('MUSIC_CHANNEL_ID')
                    channel_msg_id = None
                    file_id_to_send = document

                    if music_channel_id:
                        try:
                            channel_msg = await bot.send_document(
                                chat_id=music_channel_id,
                                document=document,
                                caption=f"@Spotizer_bot 🎧\n📋 {collection.title} - {collection.artist}"
                            )
                            channel_msg_id = channel_msg.message_id
                            file_id_to_send = channel_msg.document.file_id
                        except Exception as e:
                            logger.error(f"Failed to send to music channel: {e}")

                    sent_message = await bot.send_document(
                        chat_id=user_id, 
                        document=file_id_to_send, 
                        caption=f"@Spotizer_bot 🎧"
                    )
                    
                    await self.add_download(
                        user_id=user_id,
                        yt_id=yt_id,
                        content_type=content_type,
                        file_id=sent_message.document.file_id,
                        quality=quality,
                        url=url,
                        title=collection.title,
                        artist=collection.artist,
                        album=collection.title if smart.album else None,
                        channel_id=int(music_channel_id) if music_channel_id else None,
                        message_id=channel_msg_id
                    )
                    
                    if os.path.exists(file_path):
                        os.remove(file_path)
            else:
                track_ids = await self.yt_dlp_service.get_track_list(content_type, yt_id)
                musics_playlist = []
                
                for t_id in track_ids:
                    try:
                        track = await self.get_track(str(t_id))
                        if track:
                            download_id = await self.add_download(
                                user_id=user_id,
                                yt_id=t_id,
                                content_type="track",
                                file_id=track.file_id,
                                quality=quality,
                                url=track.url,
                                title=track.title,
                                artist=track.artist,
                                duration=track.duration,
                                file_name=None,
                                album=track.album,
                            )
                            await bot.send_audio(
                                chat_id=user_id,
                                audio=track.file_id,
                                caption=f"@Spotizer_bot 🎧",
                                title=track.title,
                                performer=track.artist,
                                reply_markup=MusicView.get_rating_keyboard(download_id)
                            )
                            musics_playlist.append((track.title, track.duration, None))
                        else:
                            track_link = f"https://music.youtube.com/watch?v={t_id}"
                            smart = await self.yt_dlp_service.download(track_link, quality_download=quality, make_zip=False)
                            
                            if smart.track:
                                file_path = smart.track.song_path
                                try:
                                    audio_file = FSInputFile(file_path)
                                    duration = self.file_handler.get_audio_duration(file_path)
                                    
                                    title = smart.track.music
                                    artist = smart.track.artist
                                    album = smart.track.album

                                    music_channel_id = os.getenv('MUSIC_CHANNEL_ID')
                                    channel_msg_id = None
                                    file_id_to_send = audio_file

                                    if music_channel_id:
                                        try:
                                            channel_msg = await bot.send_audio(
                                                chat_id=music_channel_id,
                                                audio=audio_file,
                                                caption=f"@Spotizer_bot 🎧\n{title} - {artist}",
                                                duration=duration,
                                                title=title,
                                                performer=artist
                                            )
                                            channel_msg_id = channel_msg.message_id
                                            file_id_to_send = channel_msg.audio.file_id
                                        except Exception as e:
                                            logger.error(f"Failed to send to music channel: {e}")

                                    sent_message = await bot.send_audio(
                                        chat_id=user_id,
                                        audio=file_id_to_send,
                                        caption=f"@Spotizer_bot 🎧",
                                        duration=duration,
                                        title=title,
                                        performer=artist,
                                    )

                                    await self.add_track(
                                        track_id=str(t_id),
                                        url=track_link,
                                        file_id=sent_message.audio.file_id,
                                        title=title,
                                        artist=artist,
                                        album=album,
                                        duration=duration,
                                        quality=quality,
                                        channel_id=int(music_channel_id) if music_channel_id else None,
                                        message_id=channel_msg_id,
                                    )
                                    
                                    download_id = await self.add_download(
                                        user_id=user_id,
                                        yt_id=t_id,
                                        content_type='track',
                                        file_id=sent_message.audio.file_id,
                                        quality=quality,
                                        url=track_link,
                                        title=title,
                                        artist=artist,
                                        duration=duration,
                                        file_name=sent_message.audio.file_name,
                                        album=album,
                                        channel_id=int(music_channel_id) if music_channel_id else None,
                                        message_id=channel_msg_id
                                    )
                                    
                                    await sent_message.edit_reply_markup(
                                        reply_markup=MusicView.get_rating_keyboard(download_id)
                                    )
                                    
                                    musics_playlist.append((title, duration, sent_message.audio.file_name))
                                except Exception as e:
                                    logger.error(f"Download processing error: {str(e)}", exc_info=True)
                                finally:
                                    if os.path.exists(file_path):
                                        os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Error processing track {t_id}: {str(e)}", exc_info=True)

                if len(musics_playlist) > 1:
                    filename = f'ytmusic_{yt_id}.m3u'
                    await self.file_handler.playlist_creator(musics_playlist, filename)
                    
                    await bot.send_document(
                        chat_id=user_id,
                        document=FSInputFile(filename),
                        caption="<a href='https://telegra.ph/How-to-Use-M3U-Playlists-03-02'>What is this and how can I use it?</a>\n\n@Spotizer_bot 🎧",
                        parse_mode='HTML'
                    )
                    
                    if os.path.exists(filename):
                        os.remove(filename)

            return True, "Download completed successfully"

        except Exception as e:
            logger.error(f"Download processing error: {str(e)}", exc_info=True)
            await bot.send_message(
                chat_id=user_id,
                text="An unexpected error occurred. Please try again later."
            )
            return False, "An error occurred while processing your download request."

    @staticmethod
    async def get_user_downloads(user_id, limit=5, offset=0):
        async with async_session_maker() as session:
            result = await session.execute(
                select(UserDownload)
                .where(UserDownload.user_id == user_id)
                .order_by(UserDownload.downloaded_at.desc())
                .offset(offset)
                .limit(limit)
            )
            downloads = result.scalars().all()
            return True, downloads

    @staticmethod
    async def update_download_rating(user_id: int, download_id: int, rating: int) -> tuple[bool, str]:
        async with async_session_maker() as session:
            async with session.begin():
                result = await session.execute(
                    select(UserDownload).where(
                        UserDownload.download_id == download_id,
                        UserDownload.user_id == user_id
                    )
                )
                download = result.scalars().first()
                if download:
                    download.user_rating = rating if rating != 0 else None
                    return True, "Rating updated"
                return False, "Download not found"

    async def get_artist_top_tracks(self, artist_id: str) -> list:
        try:
            logger.info(f"Getting top tracks for artist {artist_id}")
            artist_info = await self.ytmusic_service.get_item_info('artist', artist_id)
            if artist_info and 'more_artist_info' in artist_info:
                return artist_info['more_artist_info'].get('top_tracks', [])
            return []
        except Exception as e:
            logger.error(f"Error getting artist top tracks: {str(e)}", exc_info=True)
            return []

    async def get_artist_albums(self, artist_id: str) -> list:
        try:
            logger.info(f"Getting albums for artist {artist_id}")
            artist_info = await self.ytmusic_service.get_item_info('artist', artist_id)
            if artist_info and 'more_artist_info' in artist_info:
                return artist_info['more_artist_info'].get('albums', [])
            return []
        except Exception as e:
            logger.error(f"Error getting artist albums: {str(e)}", exc_info=True)
            return []
