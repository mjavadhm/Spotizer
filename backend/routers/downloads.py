import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from ..database import get_async_db
from ..models.user import User
from ..models.download import UserDownload
from ..models.track import Track
from ..schemas.download import (
    DownloadRequest, DownloadResponse, DownloadHistoryResponse,
    DownloadHistoryItem, PopularDownloadsResponse, PopularDownloadItem
)
from ..services.deezer_service import get_deezer_service
from ..dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/downloads", tags=["Downloads"])


@router.get("/history", response_model=DownloadHistoryResponse)
async def get_download_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get user's download history"""
    offset = (page - 1) * page_size

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(UserDownload).where(
            UserDownload.user_id == current_user.user_id
        )
    )
    total = count_result.scalar()

    # Get downloads
    result = await db.execute(
        select(UserDownload)
        .where(UserDownload.user_id == current_user.user_id)
        .order_by(desc(UserDownload.downloaded_at))
        .offset(offset)
        .limit(page_size)
    )
    downloads = result.scalars().all()

    has_more = offset + page_size < total

    logger.info(f"Retrieved {len(downloads)} downloads for user {current_user.user_id}")

    return DownloadHistoryResponse(
        downloads=[DownloadHistoryItem.model_validate(d) for d in downloads],
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more
    )


@router.get("/history/{download_id}", response_model=DownloadHistoryItem)
async def get_download_detail(
    download_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get details of a specific download"""
    result = await db.execute(
        select(UserDownload).where(
            UserDownload.download_id == download_id,
            UserDownload.user_id == current_user.user_id
        )
    )
    download = result.scalar_one_or_none()

    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download not found"
        )

    return download


@router.get("/popular", response_model=PopularDownloadsResponse)
async def get_popular_downloads(
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    db: AsyncSession = Depends(get_async_db)
):
    """Get most popular downloads"""
    result = await db.execute(
        select(Track)
        .order_by(desc(Track.download_count))
        .limit(limit)
    )
    tracks = result.scalars().all()

    return PopularDownloadsResponse(
        tracks=[PopularDownloadItem.model_validate(t) for t in tracks]
    )


@router.post("/request", response_model=DownloadResponse)
async def request_download(
    request: DownloadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Request a download for a track, album, or playlist.

    This endpoint validates the URL and returns download information.
    The actual file download would be handled by the Telegram bot.
    """
    try:
        deezer = get_deezer_service()

        # Check if it's a Spotify URL and convert
        url = request.url
        if 'spotify.com' in url:
            converted_url = deezer.convert_spotify_to_deezer(url)
            if not converted_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not convert Spotify URL to Deezer"
                )
            url = converted_url

        # Extract info from URL
        content_type, deezer_id = deezer.extract_info_from_url(url)

        if not content_type or not deezer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL. Please provide a valid Deezer or Spotify link."
            )

        # Get info from Deezer
        if content_type == 'track':
            info = await deezer.get_track_info(deezer_id)
        elif content_type == 'album':
            info = await deezer.get_album_info(deezer_id)
        elif content_type == 'playlist':
            info = await deezer.get_playlist_info(deezer_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported content type: {content_type}"
            )

        if not info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{content_type.capitalize()} not found on Deezer"
            )

        # Check if already downloaded
        result = await db.execute(
            select(UserDownload).where(
                UserDownload.user_id == current_user.user_id,
                UserDownload.deezer_id == deezer_id,
                UserDownload.content_type == content_type
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return DownloadResponse(
                success=True,
                message="Already in your download history",
                content_type=content_type,
                deezer_id=deezer_id,
                title=info.get('title'),
                artist=info.get('artist') or info.get('creator'),
                file_id=existing.file_id
            )

        logger.info(f"Download requested: {content_type} {deezer_id} by user {current_user.user_id}")

        return DownloadResponse(
            success=True,
            message=f"{content_type.capitalize()} found. Use the Telegram bot to download.",
            content_type=content_type,
            deezer_id=deezer_id,
            title=info.get('title'),
            artist=info.get('artist') or info.get('creator')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download request error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process download request: {str(e)}"
        )


@router.get("/check/{deezer_id}")
async def check_download_exists(
    deezer_id: int,
    content_type: str = Query("track", description="Content type: track, album, or playlist"),
    quality: Optional[str] = Query(None, description="Download quality"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Check if a track/album/playlist has already been downloaded"""
    query = select(UserDownload).where(
        UserDownload.user_id == current_user.user_id,
        UserDownload.deezer_id == deezer_id,
        UserDownload.content_type == content_type
    )

    if quality:
        query = query.where(UserDownload.quality == quality)

    result = await db.execute(query)
    download = result.scalar_one_or_none()

    if download:
        return {
            "exists": True,
            "download": DownloadHistoryItem.model_validate(download)
        }

    return {"exists": False}


@router.delete("/history/{download_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_download_from_history(
    download_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a download from history"""
    result = await db.execute(
        select(UserDownload).where(
            UserDownload.download_id == download_id,
            UserDownload.user_id == current_user.user_id
        )
    )
    download = result.scalar_one_or_none()

    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Download not found"
        )

    await db.delete(download)
    await db.commit()

    logger.info(f"Deleted download {download_id} for user {current_user.user_id}")
