from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime


class DownloadRequest(BaseModel):
    url: str
    quality: Optional[str] = "MP3_320"
    make_zip: Optional[bool] = None


class DownloadResponse(BaseModel):
    success: bool
    message: str
    content_type: Optional[str] = None
    deezer_id: Optional[int] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    file_id: Optional[str] = None


class DownloadHistoryItem(BaseModel):
    download_id: int
    deezer_id: int
    content_type: str
    file_id: str
    quality: str
    url: Optional[str] = None
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    duration: Optional[int] = None
    file_name: Optional[str] = None
    downloaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DownloadHistoryResponse(BaseModel):
    downloads: List[DownloadHistoryItem]
    total: int
    page: int
    page_size: int
    has_more: bool


class PopularDownloadItem(BaseModel):
    track_id: int
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    download_count: int

    class Config:
        from_attributes = True


class PopularDownloadsResponse(BaseModel):
    tracks: List[PopularDownloadItem]
