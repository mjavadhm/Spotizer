from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ArtistInfo(BaseModel):
    id: str
    name: str


class AlbumInfo(BaseModel):
    id: str
    name: str
    images: Optional[List[dict]] = None
    release_date: Optional[str] = None


class TrackBase(BaseModel):
    track_id: int
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    duration: Optional[int] = None
    quality: Optional[str] = None


class TrackResponse(TrackBase):
    file_id: Optional[str] = None
    url: Optional[str] = None
    download_count: int = 0
    last_downloaded: Optional[datetime] = None

    class Config:
        from_attributes = True


class TrackSearchResult(BaseModel):
    id: str
    name: str
    artists: List[ArtistInfo]
    main_artist: str
    duration_ms: int
    duration: str
    album: AlbumInfo
    preview_url: Optional[str] = None
    type: str = "track"


class AlbumSearchResult(BaseModel):
    id: str
    name: str
    artists: List[ArtistInfo]
    main_artist: str
    total_tracks: int
    release_date: str
    images: Optional[List[dict]] = None
    type: str = "album"


class PlaylistSearchResult(BaseModel):
    id: str
    name: str
    owner: dict
    total_tracks: int
    images: Optional[List[dict]] = None
    type: str = "playlist"


class ArtistSearchResult(BaseModel):
    id: str
    name: str
    followers: int
    genres: List[str]
    popularity: int
    images: Optional[List[dict]] = None
    type: str = "artist"


class TrackDetailResponse(BaseModel):
    id: str
    name: str
    artists: List[ArtistInfo]
    main_artist: str
    url: str
    duration_ms: int
    duration: str
    explicit: bool
    image: Optional[str] = None
    album: dict
    preview_url: Optional[str] = None
    popularity: int
    type: str = "track"


class AlbumDetailResponse(BaseModel):
    id: str
    name: str
    artists: List[ArtistInfo]
    main_artist: str
    release_date: str
    total_tracks: int
    image: Optional[str] = None
    images: Optional[List[dict]] = None
    tracks: List[dict]
    type: str = "album"
    url: str


class PlaylistDetailResponse(BaseModel):
    id: str
    name: str
    owner: dict
    description: Optional[str] = None
    total_tracks: int
    image: Optional[str] = None
    images: Optional[List[dict]] = None
    tracks: List[dict]
    url: str
    type: str = "playlist"


class ArtistDetailResponse(BaseModel):
    id: str
    name: str
    followers: int
    genres: List[str]
    popularity: int
    image: Optional[str] = None
    url: str
    type: str = "artist"
    more_artist_info: Optional[dict] = None
