import os
import asyncio
import yt_dlp
from dataclasses import dataclass
from typing import Optional, List
from utils.file_handler import FileHandler
from logger import get_logger

logger = get_logger(__name__)

@dataclass
class DownloadResultTrack:
    song_path: str
    music: str
    artist: str
    album: str

@dataclass
class DownloadResultCollection:
    zip_path: str
    title: str
    artist: str

@dataclass
class SmartResult:
    track: Optional[DownloadResultTrack] = None
    album: Optional[DownloadResultCollection] = None
    playlist: Optional[DownloadResultCollection] = None

class YTDlpService:
    def __init__(self):
        self.file_handler = FileHandler()
        logger.info("YTDlpService initialized")

    async def download(self, url: str, output_folder="downloads", quality_download: str = 'MP3_320', make_zip: bool = False) -> SmartResult:
        """Download track/album/playlist using yt-dlp"""
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            
        def _download():
            audio_bitrate = '320' if quality_download == 'MP3_320' else '128'
            
            ydl_opts = {
                'cookiefile': 'cookies.txt',
                'format': 'bestaudio/bestvideo+bestaudio/best',
                'extractor_args': {'youtube': {'client': ['android', 'web']}},
                'outtmpl': f'{output_folder}/%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': audio_bitrate,
                }],
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_playlist' if not make_zip else False,
            }
            
            if make_zip:
                import uuid
                subfolder = os.path.join(output_folder, f"playlist_download_{uuid.uuid4().hex}")
                if not os.path.exists(subfolder):
                    os.makedirs(subfolder)
                ydl_opts['outtmpl'] = f'{subfolder}/%(title)s.%(ext)s'
                ydl_opts['extract_flat'] = False
            else:
                subfolder = output_folder
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=True)
                except Exception as e:
                    logger.error(f"yt-dlp extract_info error: {e}")
                    return SmartResult()
                
                if 'entries' in info:
                    # It's a playlist or album
                    title = info.get('title', 'Unknown Collection')
                    artist = info.get('uploader', 'Unknown Artist')
                    
                    if make_zip:
                        files_to_zip = []
                        for entry in info['entries']:
                            if entry:
                                expected_path = os.path.join(subfolder, f"{entry.get('title')}.mp3")
                                if os.path.exists(expected_path):
                                    files_to_zip.append(expected_path)
                                else:
                                    # Try to find by listdir just in case outtmpl resulted in different name
                                    pass
                        
                        # Gather all mp3s in the subfolder
                        files_to_zip = [os.path.join(subfolder, f) for f in os.listdir(subfolder) if f.endswith('.mp3')]
                        
                        zip_name = f"{title}.zip"
                        success, zip_path = self.file_handler.create_zip_archive(files_to_zip, zip_name)
                        
                        # Cleanup individual mp3s and subfolder
                        for f in files_to_zip:
                            try:
                                os.remove(f)
                            except:
                                pass
                        try:
                            os.rmdir(subfolder)
                        except:
                            pass
                            
                        if success:
                            collection = DownloadResultCollection(zip_path=zip_path, title=title, artist=artist)
                            if 'album' in url.lower() or 'browse' in url.lower():
                                return SmartResult(album=collection)
                            else:
                                return SmartResult(playlist=collection)
                    
                    return SmartResult()
                else:
                    # Single track
                    title = info.get('title', 'Unknown Track')
                    artist = info.get('uploader', 'Unknown Artist')
                    album = info.get('album', 'Unknown Album')
                    
                    # yt-dlp might sanitize titles, so let's find the most recent mp3 or just use a generic way
                    # Better to let YTDL return the exact filename if we can, or just grab the file that was downloaded.
                    # As a workaround, we'll get the info's requested_downloads
                    file_path = None
                    if 'requested_downloads' in info:
                        filepath_pre = info['requested_downloads'][0]['filepath']
                        # change extension to mp3
                        file_path = os.path.splitext(filepath_pre)[0] + '.mp3'
                    else:
                        file_path = os.path.join(output_folder, f"{title}.mp3")
                    
                    if not os.path.exists(file_path):
                        logger.error(f"Could not find downloaded file at {file_path}")
                        # Fallback try to find in folder with title
                        for f in os.listdir(output_folder):
                            if title in f and f.endswith('.mp3'):
                                file_path = os.path.join(output_folder, f)
                                break
                    
                    track = DownloadResultTrack(
                        song_path=file_path,
                        music=title,
                        artist=artist,
                        album=album
                    )
                    return SmartResult(track=track)

        try:
            return await asyncio.to_thread(_download)
        except Exception as e:
            logger.error(f"Download error for URL {url}: {str(e)}", exc_info=True)
            return SmartResult()
            
    async def get_track_list(self, content_type: str, item_id: str) -> List[str]:
        """Get list of track IDs from album or playlist"""
        from services.ytmusic_service import YTMusicService
        yt_service = YTMusicService()
        
        if content_type == 'track':
            return [item_id]
            
        info = await yt_service.get_item_info(content_type, item_id)
        if info and 'tracks' in info:
            return [track['id'] for track in info['tracks'] if track.get('id')]
            
        return []
