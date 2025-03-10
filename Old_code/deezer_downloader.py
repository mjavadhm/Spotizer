arl = "ca15ae9aa597cde5ee33f72871711b57b3a9efe2bdf2a6d03283f2382ae87d4e0a12faf2e2266f2faba1b9dd912cf3314773b049fba1c3c286cb878def73501766ee540f9a608ed0708e696534461d878c37e5908edea1edb49fa38c4ad2b4b0"
#ca15ae9aa597cde5ee33f72871711b57b3a9efe2bdf2a6d03283f2382ae87d4e0a12faf2e2266f2faba1b9dd912cf3314773b049fba1c3c286cb878def73501766ee540f9a608ed0708e696534461d878c37e5908edea1edb49fa38c4ad2b4b0
#3e040ae9e2667f24640886dceac9b00b63113049b642af2f92bf44a8964dbfcc2a22f7638c64c9c917420fd8fc34568be19f487d33145bec3c58131ffe93ebe3a233d8b00bb2ab9255acee2c04b43c2a07df7547d6960637b6ae1de2e83de1ac
# deezer_downloader.py
import os
import re
from typing import Optional, Union
from deezloader.deezloader import DeeLogin
from dotenv import load_dotenv
load_dotenv()
# Replace with your actual ARL token
ARL = os.getenv("ARL")
SARL = os.getenv("SARL")
downloader = DeeLogin(arl=SARL)
convert_spoty_to_dee_link_track = downloader.convert_spoty_to_dee_link_track
convert_spoty_to_dee_link_album = downloader.convert_spoty_to_dee_link_album

class Track:
    def __init__(
        self,
        tags: dict,
        song_path: str,
        file_format: str,
        quality: str,
        link: str,
        ids: int
    ) -> None:
        self.tags = tags
        self.__set_tags()
        self.song_name = f"{self.title} - {self.artist}"
        self.song_path = song_path
        self.file_format = file_format
        self.quality = quality
        self.link = link
        self.ids = ids
        self.md5_image = None
        self.success = True
        self.__set_track_md5()

    def __set_tags(self):
        for tag, value in self.tags.items():
            setattr(
                self, tag, value
            )

    def __set_track_md5(self):
        self.track_md5 = f"track/{self.ids}"

    def set_fallback_ids(self, fallback_ids):
        self.fallback_ids = fallback_ids
        self.fallback_track_md5 = f"track/{self.fallback_ids}"


class Album:
    def __init__(self, ids: int) -> None:
        self.tracks: list[Track] = []
        self.zip_path = None
        self.image = None
        self.album_quality = None
        self.md5_image = None
        self.ids = ids
        self.nb_tracks = None
        self.title = None
        self.artist = None
        self.upc = None
        self.tags = None
        self.__set_album_md5()

    def __set_album_md5(self):
        self.album_md5 = f"album/{self.ids}"


class Playlist:
    def __init__(self, ids: int) -> None:
        self.tracks: list[Track] = []
        self.zip_path = None
        self.ids = ids
        self.title = None


class Smart:
    def __init__(self) -> None:
        self.track: Optional[Track] = None
        self.album: Optional[Album] = None
        self.playlist: Optional[Playlist] = None
        self.type = None
        self.source = None


# Initialize the Deezer downloader

def extract_id_from_link(link: str) -> tuple:
    """Extract content type and ID from Deezer URL"""
    patterns = {
        'track': r'deezer\.com(?:\/[a-z]{2})?\/track\/(\d+)',
        'album': r'deezer\.com(?:\/[a-z]{2})?\/album\/(\d+)',
        'playlist': r'deezer\.com(?:\/[a-z]{2})?\/playlist\/(\d+)'
    }
    
    for content_type, pattern in patterns.items():
        match = re.search(pattern, link)
        if match:
            return content_type, int(match.group(1))
    
    return None, None


def download_song_from_link(link: str, output_folder="downloads", quality_download="MP3_320", make_zip=True) -> Smart:
    """
    Download music from Deezer link and return a Smart object with the results
    
    Args:
        link (str): Deezer link (track, album or playlist)
        output_folder (str): Folder to save the downloaded files
        quality_download (str): Quality of the downloaded files (MP3_128, MP3_320, FLAC)
        make_zip (bool): Make a zip file for albums and playlists
        
    Returns:
        Smart: Object containing the downloaded track, album or playlist
    """
    try:
        smart = downloader.download_smart(link, output_folder, quality_download="MP3_320", make_zip=make_zip)
        return smart
    
    except Exception as e:
        raise Exception(f"Error downloading from Deezer: {str(e)}")
    


if __name__ == "__main__":
    # Test the downloader
    test_links = [
        "https://www.deezer.com/track/1341166",
        "https://www.deezer.com/us/album/6902564",
        "https://www.deezer.com/us/playlist/1963962142"
    ]
    
    for link in test_links:
        print(f"Testing download for: {link}")
        try:
            smart = download_song_from_link(link, output_folder="test_downloads")
            if smart.track:
                print(f"Track downloaded: {smart.track.song_name}")
                print(f"File path: {smart.track.song_path}")
            elif smart.album:
                print(f"Album downloaded: {smart.album.title} by {smart.album.artist}")
                print(f"Number of tracks: {len(smart.album.tracks)}")
                if smart.album.zip_path:
                    print(f"ZIP file path: {smart.album.zip_path}")
            elif smart.playlist:
                print(f"Playlist downloaded: {smart.playlist.title}")
                print(f"Number of tracks: {len(smart.playlist.tracks)}")
                if smart.playlist.zip_path:
                    print(f"ZIP file path: {smart.playlist.zip_path}")
            else:
                print("No download was successful")
        except Exception as e:
            print(f"Error: {str(e)}")
        print("\n" + "-"*50 + "\n")