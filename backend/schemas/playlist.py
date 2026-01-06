from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class PlaylistTrackBase(BaseModel):
    track_deezer_id: int


class PlaylistTrackResponse(PlaylistTrackBase):
    playlist_track_id: int
    added_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlaylistBase(BaseModel):
    name: str
    description: Optional[str] = None


class PlaylistCreate(PlaylistBase):
    pass


class PlaylistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class PlaylistResponse(PlaylistBase):
    playlist_id: int
    user_id: int
    uuid: UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlaylistWithTracks(PlaylistResponse):
    tracks: List[PlaylistTrackResponse] = []


class AddTrackToPlaylist(BaseModel):
    track_deezer_id: int


class RemoveTrackFromPlaylist(BaseModel):
    track_deezer_id: int


class PlaylistListResponse(BaseModel):
    playlists: List[PlaylistResponse]
    total: int
