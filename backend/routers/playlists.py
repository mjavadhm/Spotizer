import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload

from ..database import get_async_db
from ..models.user import User
from ..models.playlist import Playlist, PlaylistTrack
from ..schemas.playlist import (
    PlaylistCreate, PlaylistUpdate, PlaylistResponse,
    PlaylistWithTracks, AddTrackToPlaylist, PlaylistListResponse,
    PlaylistTrackResponse, RemoveTrackFromPlaylist
)
from ..dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playlists", tags=["Playlists"])


@router.get("", response_model=PlaylistListResponse)
async def get_my_playlists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get all playlists for the current user"""
    result = await db.execute(
        select(Playlist)
        .where(Playlist.user_id == current_user.user_id)
        .order_by(Playlist.created_at.desc())
    )
    playlists = result.scalars().all()

    logger.info(f"Retrieved {len(playlists)} playlists for user {current_user.user_id}")

    return PlaylistListResponse(
        playlists=[PlaylistResponse.model_validate(p) for p in playlists],
        total=len(playlists)
    )


@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    playlist_data: PlaylistCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Create a new playlist"""
    # Check if playlist with same name exists
    result = await db.execute(
        select(Playlist).where(
            Playlist.user_id == current_user.user_id,
            Playlist.name == playlist_data.name
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Playlist with this name already exists"
        )

    playlist = Playlist(
        user_id=current_user.user_id,
        name=playlist_data.name,
        description=playlist_data.description
    )
    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)

    logger.info(f"Created playlist '{playlist.name}' for user {current_user.user_id}")

    return playlist


@router.get("/{playlist_id}", response_model=PlaylistWithTracks)
async def get_playlist(
    playlist_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get a specific playlist with its tracks"""
    result = await db.execute(
        select(Playlist)
        .options(selectinload(Playlist.tracks))
        .where(
            Playlist.playlist_id == playlist_id,
            Playlist.user_id == current_user.user_id
        )
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )

    return playlist


@router.get("/uuid/{playlist_uuid}", response_model=PlaylistWithTracks)
async def get_playlist_by_uuid(
    playlist_uuid: UUID,
    db: AsyncSession = Depends(get_async_db)
):
    """Get a playlist by its UUID (public access)"""
    result = await db.execute(
        select(Playlist)
        .options(selectinload(Playlist.tracks))
        .where(Playlist.uuid == playlist_uuid)
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )

    return playlist


@router.patch("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: int,
    playlist_update: PlaylistUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update a playlist"""
    result = await db.execute(
        select(Playlist).where(
            Playlist.playlist_id == playlist_id,
            Playlist.user_id == current_user.user_id
        )
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )

    update_data = playlist_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data to update"
        )

    # Check for duplicate name
    if 'name' in update_data and update_data['name'] != playlist.name:
        existing = await db.execute(
            select(Playlist).where(
                Playlist.user_id == current_user.user_id,
                Playlist.name == update_data['name'],
                Playlist.playlist_id != playlist_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Playlist with this name already exists"
            )

    stmt = (
        update(Playlist)
        .where(Playlist.playlist_id == playlist_id)
        .values(**update_data)
    )
    await db.execute(stmt)
    await db.commit()
    await db.refresh(playlist)

    logger.info(f"Updated playlist {playlist_id} for user {current_user.user_id}")

    return playlist


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playlist(
    playlist_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a playlist"""
    result = await db.execute(
        select(Playlist).where(
            Playlist.playlist_id == playlist_id,
            Playlist.user_id == current_user.user_id
        )
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )

    await db.delete(playlist)
    await db.commit()

    logger.info(f"Deleted playlist {playlist_id} for user {current_user.user_id}")


@router.post("/{playlist_id}/tracks", response_model=PlaylistTrackResponse, status_code=status.HTTP_201_CREATED)
async def add_track_to_playlist(
    playlist_id: int,
    track_data: AddTrackToPlaylist,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Add a track to a playlist"""
    # Verify playlist exists and belongs to user
    result = await db.execute(
        select(Playlist).where(
            Playlist.playlist_id == playlist_id,
            Playlist.user_id == current_user.user_id
        )
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )

    # Check if track already in playlist
    result = await db.execute(
        select(PlaylistTrack).where(
            PlaylistTrack.playlist_id == playlist_id,
            PlaylistTrack.track_deezer_id == track_data.track_deezer_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Track already in playlist"
        )

    playlist_track = PlaylistTrack(
        playlist_id=playlist_id,
        track_deezer_id=track_data.track_deezer_id
    )
    db.add(playlist_track)
    await db.commit()
    await db.refresh(playlist_track)

    logger.info(f"Added track {track_data.track_deezer_id} to playlist {playlist_id}")

    return playlist_track


@router.delete("/{playlist_id}/tracks/{track_deezer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_track_from_playlist(
    playlist_id: int,
    track_deezer_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Remove a track from a playlist"""
    # Verify playlist exists and belongs to user
    result = await db.execute(
        select(Playlist).where(
            Playlist.playlist_id == playlist_id,
            Playlist.user_id == current_user.user_id
        )
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )

    # Find and delete the track
    result = await db.execute(
        select(PlaylistTrack).where(
            PlaylistTrack.playlist_id == playlist_id,
            PlaylistTrack.track_deezer_id == track_deezer_id
        )
    )
    playlist_track = result.scalar_one_or_none()

    if not playlist_track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found in playlist"
        )

    await db.delete(playlist_track)
    await db.commit()

    logger.info(f"Removed track {track_deezer_id} from playlist {playlist_id}")


@router.get("/{playlist_id}/tracks", response_model=List[PlaylistTrackResponse])
async def get_playlist_tracks(
    playlist_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get all tracks in a playlist"""
    # Verify playlist exists and belongs to user
    result = await db.execute(
        select(Playlist).where(
            Playlist.playlist_id == playlist_id,
            Playlist.user_id == current_user.user_id
        )
    )
    playlist = result.scalar_one_or_none()

    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )

    result = await db.execute(
        select(PlaylistTrack)
        .where(PlaylistTrack.playlist_id == playlist_id)
        .order_by(PlaylistTrack.added_at.desc())
    )
    tracks = result.scalars().all()

    return tracks
