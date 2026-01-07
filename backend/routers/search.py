import logging
from typing import Optional
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query

from ..schemas.search import SearchType, SearchResponse
from ..schemas.track import (
    TrackDetailResponse, AlbumDetailResponse,
    PlaylistDetailResponse, ArtistDetailResponse
)
from ..services.spotify_service import get_spotify_service, SpotifyService
from ..services.deezer_service import get_deezer_service, DeezerService
from ..services.download_queue import download_queue
from ..dependencies import get_current_user_optional
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=SearchResponse)
async def search(
    query: Optional[str] = Query(None, min_length=1, description="Search query", alias="query"),
    q: Optional[str] = Query(None, min_length=1, description="Search query (alias)"),
    search_type: Optional[SearchType] = Query(None, description="Type of content to search"),
    type: Optional[SearchType] = Query(None, description="Type of content to search (alias)"),
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    # Handle parameter aliases
    search_query = query or q
    if not search_query:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Search query is required (use 'query' or 'q' parameter)")
    query = search_query  # Use the resolved query for the rest of the function
    
    # Handle search_type alias
    resolved_type = search_type or type or SearchType.TRACK
    
    # Search for music content on Spotify.
    # Supports: Tracks, Albums, Playlists, Artists
    try:
        spotify = get_spotify_service()
        results = await spotify.search(
            query=query,
            search_type=resolved_type.value,
            limit=limit,
            offset=offset
        )

        has_more = len(results) == limit

        logger.info(f"Search query: '{query}', type: {resolved_type}, results: {len(results)}")

        # Trigger background download for track results
        if resolved_type == SearchType.TRACK and results:
            asyncio.create_task(download_queue.add_batch(
                tracks=results,
                priority=download_queue.PRIORITY_LOW,
                max_items=10  # Pre-download top 10 results
            ))

        return SearchResponse(
            query=query,
            search_type=resolved_type.value,
            results=results,
            total=len(results),
            limit=limit,
            offset=offset,
            has_more=has_more
        )

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/tracks/{track_id}")
async def get_track_info(
    track_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get detailed information about a track"""
    try:
        spotify = get_spotify_service()
        info = await spotify.get_item_info('track', track_id)

        if not info:
            raise HTTPException(
                status_code=404,
                detail="Track not found"
            )

        return info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting track info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get track info: {str(e)}"
        )


@router.get("/albums/{album_id}")
async def get_album_info(
    album_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get detailed information about an album"""
    try:
        spotify = get_spotify_service()
        info = await spotify.get_item_info('album', album_id)

        if not info:
            raise HTTPException(
                status_code=404,
                detail="Album not found"
            )

        # Trigger background download for album tracks
        if 'tracks' in info and 'items' in info['tracks']:
            tracks = info['tracks']['items']
            asyncio.create_task(download_queue.add_batch(
                tracks=tracks,
                priority=download_queue.PRIORITY_LOW,
                max_items=20  # Limit to 20 tracks for albums
            ))

        return info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting album info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get album info: {str(e)}"
        )


@router.get("/playlists/{playlist_id}")
async def get_playlist_info(
    playlist_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get detailed information about a playlist"""
    try:
        spotify = get_spotify_service()
        info = await spotify.get_item_info('playlist', playlist_id)

        if not info:
            raise HTTPException(
                status_code=404,
                detail="Playlist not found"
            )

        # Trigger background download for playlist tracks
        if 'tracks' in info and 'items' in info['tracks']:
            # Playlist tracks might have a different structure (wrapped in 'track' object)
            raw_tracks = info['tracks']['items']
            tracks = []
            for item in raw_tracks:
                if 'track' in item and item['track']:
                    tracks.append(item['track'])
                elif 'id' in item: # Maybe it's a direct track list
                    tracks.append(item)
            
            if tracks:
                asyncio.create_task(download_queue.add_batch(
                    tracks=tracks,
                    priority=download_queue.PRIORITY_LOW,
                    max_items=20  # Limit to 20 tracks for playlists
                ))

        return info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting playlist info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get playlist info: {str(e)}"
        )


@router.get("/artists/{artist_id}")
async def get_artist_info(
    artist_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get detailed information about an artist including top tracks and albums"""
    try:
        spotify = get_spotify_service()
        info = await spotify.get_item_info('artist', artist_id)

        if not info:
            raise HTTPException(
                status_code=404,
                detail="Artist not found"
            )

        return info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting artist info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get artist info: {str(e)}"
        )


@router.get("/deezer/track/{track_id}")
async def get_deezer_track_info(
    track_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get track information from Deezer"""
    try:
        deezer = get_deezer_service()
        info = await deezer.get_track_info(track_id)

        if not info:
            raise HTTPException(
                status_code=404,
                detail="Track not found on Deezer"
            )

        return info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Deezer track info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get track info from Deezer: {str(e)}"
        )


@router.get("/deezer/album/{album_id}")
async def get_deezer_album_info(
    album_id: int,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get album information from Deezer"""
    try:
        deezer = get_deezer_service()
        info = await deezer.get_album_info(album_id)

        if not info:
            raise HTTPException(
                status_code=404,
                detail="Album not found on Deezer"
            )

        return info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Deezer album info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get album info from Deezer: {str(e)}"
        )


@router.get("/tracks/{track_id}/recommendations")
async def get_track_recommendations(
    track_id: str,
    limit: int = Query(5, ge=1, le=20, description="Number of recommendations"),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get similar track recommendations based on a seed track"""
    try:
        spotify = get_spotify_service()
        recommendations = await spotify.get_recommendations(track_id, limit)

        return {
            "track_id": track_id,
            "recommendations": recommendations
        }

    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recommendations: {str(e)}"
        )
