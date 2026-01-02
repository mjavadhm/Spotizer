from .user import (
    UserCreate, UserUpdate, UserResponse, UserSettingsUpdate,
    UserSettingsResponse, Token, TokenData, UserBase, UserInDB,
    TelegramLoginData, TelegramBotAuth, TelegramAuthResponse
)
from .track import (
    TrackResponse, TrackSearchResult, AlbumSearchResult,
    PlaylistSearchResult, ArtistSearchResult, TrackDetailResponse,
    AlbumDetailResponse, PlaylistDetailResponse, ArtistDetailResponse
)
from .download import (
    DownloadRequest, DownloadResponse, DownloadHistoryResponse,
    DownloadHistoryItem, PopularDownloadsResponse
)
from .playlist import (
    PlaylistCreate, PlaylistUpdate, PlaylistResponse,
    PlaylistWithTracks, AddTrackToPlaylist, PlaylistListResponse,
    PlaylistTrackResponse, RemoveTrackFromPlaylist
)
from .search import SearchRequest, SearchResponse, SearchType
