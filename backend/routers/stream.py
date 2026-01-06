import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_async_db
from ..models.track import Track
from ..services.telegram_client import telegram_service

router = APIRouter(prefix="/stream", tags=["Stream"])
logger = logging.getLogger(__name__)


@router.get("/{track_id}")
async def stream_track(
    track_id: int,
    quality: str = Query("MP3_320", description="Audio quality"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Stream a track from Telegram via Telethon.
    """
    try:
        # Lookup track in DB using async SQLAlchemy
        query = select(Track).where(
            Track.track_id == track_id,
            Track.quality == quality
        )
        result = await db.execute(query)
        track = result.scalar_one_or_none()

        if not track:
            raise HTTPException(status_code=404, detail="Track not found or quality not available")

        message_id = track.message_id
        channel_id = track.channel_id

        if not message_id or not channel_id:
            raise HTTPException(status_code=404, detail="Track source not available (message_id/channel_id missing)")

        # Get stream generator from Telethon
        file_iterator = await telegram_service.get_file_stream(message_id, channel_id)

        if not file_iterator:
            raise HTTPException(status_code=404, detail="File content not found in Telegram")

        # Determine media type based on quality
        media_type = "audio/mpeg"  # Default to MP3
        if "flac" in quality.lower():
            media_type = "audio/flac"

        return StreamingResponse(file_iterator, media_type=media_type)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming track {track_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during streaming")


@router.get("/download/{track_id}")
async def download_track(
    track_id: int,
    quality: str = Query("MP3_320", description="Audio quality"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Download a track from Telegram via Telethon.
    """
    try:
        # Lookup track in DB using async SQLAlchemy
        query = select(Track).where(
            Track.track_id == track_id,
            Track.quality == quality
        )
        result = await db.execute(query)
        track = result.scalar_one_or_none()

        if not track:
            raise HTTPException(status_code=404, detail="Track not found or quality not available")

        message_id = track.message_id
        channel_id = track.channel_id
        file_name = track.file_name or f"track_{track_id}.mp3"

        if not message_id or not channel_id:
            raise HTTPException(status_code=404, detail="Track source not available")

        file_iterator = await telegram_service.get_file_stream(message_id, channel_id)

        if not file_iterator:
            raise HTTPException(status_code=404, detail="File content not found in Telegram")

        media_type = "application/octet-stream"

        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"'
        }

        return StreamingResponse(file_iterator, media_type=media_type, headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading track {track_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during download")
