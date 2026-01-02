from pydantic import BaseModel
from typing import Optional, List, Union
from enum import Enum

from .track import (
    TrackSearchResult, AlbumSearchResult,
    PlaylistSearchResult, ArtistSearchResult
)


class SearchType(str, Enum):
    TRACK = "track"
    ALBUM = "album"
    PLAYLIST = "playlist"
    ARTIST = "artist"


class SearchRequest(BaseModel):
    query: str
    search_type: SearchType = SearchType.TRACK
    limit: int = 10
    offset: int = 0


class SearchResponse(BaseModel):
    query: str
    search_type: str
    results: List[Union[TrackSearchResult, AlbumSearchResult, PlaylistSearchResult, ArtistSearchResult]]
    total: int
    limit: int
    offset: int
    has_more: bool
