import logging
import re
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_async_db
from ..models.track import Track
from ..services.telegram_client import telegram_service
from ..services.download_queue import download_queue

router = APIRouter(prefix="/stream", tags=["Stream"])
logger = logging.getLogger(__name__)


def parse_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    """
    Parse Range header and return (start, end) byte positions.
    Supports format: bytes=start-end, bytes=start-, bytes=-suffix
    """
    if not range_header or not range_header.startswith("bytes="):
        return 0, file_size - 1

    range_spec = range_header[6:]  # Remove "bytes="
    
    if range_spec.startswith("-"):
        # Suffix range: bytes=-500 means last 500 bytes
        suffix_length = int(range_spec[1:])
        start = max(0, file_size - suffix_length)
        end = file_size - 1
    elif range_spec.endswith("-"):
        # Open-ended range: bytes=500- means from 500 to end
        start = int(range_spec[:-1])
        end = file_size - 1
    else:
        # Full range: bytes=0-999
        parts = range_spec.split("-")
        start = int(parts[0])
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1

    # Clamp values
    start = max(0, min(start, file_size - 1))
    end = max(start, min(end, file_size - 1))

    return start, end


@router.get("/{track_id}")
async def stream_track(
    track_id: str,
    request: Request,
    quality: str = Query("MP3_320", description="Audio quality"),
    db: AsyncSession = Depends(get_async_db),
    range: Optional[str] = Header(None)
):
    """
    Stream a track from Telegram via Telethon with Range request support for seeking.
    Accepts either Spotify ID or Deezer ID (track_id).
    If Spotify ID is not found, attempts on-demand download.
    Quality is strictly forced to MP3_320.
    """
    quality = "MP3_320"
    try:
        track = None
        
        # Determine if this looks like a Spotify ID (alphanumeric with letters) or Deezer ID (numeric)
        is_spotify_id = not track_id.isdigit() and len(track_id) == 22
        
        if is_spotify_id:
            # Try to find by Spotify ID first
            query = select(Track).where(
                Track.spotify_id == str(track_id),
                Track.quality == quality
            )
            result = await db.execute(query)
            track = result.scalar_one_or_none()
        
            # If not found and it's a Spotify ID, try on-demand download
            if not track:
                logger.info(f"Track not found for Spotify ID {track_id}, triggering on-demand download...")
                try:
                    # Trigger high-priority download and wait
                    event = await download_queue.add_high_priority(spotify_id=track_id)
                    
                    # Wait for download to complete (timeout 60s)
                    await asyncio.wait_for(event.wait(), timeout=60.0)
                    
                    # Re-query database
                    result = await db.execute(query)
                    track = result.scalar_one_or_none()
                    
                    if not track:
                        raise HTTPException(status_code=404, detail="Track could not be downloaded in time.")
                        
                except asyncio.TimeoutError:
                    raise HTTPException(status_code=408, detail="Timeout waiting for track download.")
                except Exception as e:
                    logger.error(f"On-demand download failed: {e}")
                    raise HTTPException(status_code=500, detail="Failed to prepare track for streaming.")
        
        # If not found by Spotify ID (or it's a Deezer ID), try track_id
        if not track:
            query = select(Track).where(
                Track.track_id == str(track_id),
                Track.quality == quality
            )
            result = await db.execute(query)
            track = result.scalar_one_or_none()

        if not track:
            raise HTTPException(status_code=404, detail="Track not found or quality not available. Download the track first via the bot.")

        message_id = track.message_id
        channel_id = track.channel_id

        if not message_id or not channel_id:
            raise HTTPException(status_code=404, detail="Track source not available (message_id/channel_id missing)")

        # Get file info for Range requests
        message, file_size = await telegram_service.get_file_info(message_id, channel_id)
        
        if not message:
            raise HTTPException(status_code=404, detail="File content not found in Telegram")

        # Determine media type based on quality
        media_type = "audio/mpeg"  # Default to MP3
        if "flac" in quality.lower():
            media_type = "audio/flac"

        # Handle Range header for seeking
        if range and file_size > 0:
            start, end = parse_range_header(range, file_size)
            content_length = end - start + 1
            
            # Get stream with offset and limit
            file_iterator = await telegram_service.get_file_stream(
                message_id, channel_id, 
                offset=start, 
                limit=content_length
            )

            if not file_iterator:
                raise HTTPException(status_code=404, detail="File content not found in Telegram")

            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
            }

            return StreamingResponse(
                file_iterator, 
                status_code=206,  # Partial Content
                media_type=media_type,
                headers=headers
            )
        else:
            # No range request - stream entire file
            file_iterator = await telegram_service.get_file_stream(message_id, channel_id)

            if not file_iterator:
                raise HTTPException(status_code=404, detail="File content not found in Telegram")

            headers = {
                "Accept-Ranges": "bytes",
            }
            if file_size > 0:
                headers["Content-Length"] = str(file_size)

            return StreamingResponse(file_iterator, media_type=media_type, headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming track {track_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during streaming")


@router.get("/download/{track_id}")
async def download_track(
    track_id: str,
    quality: str = Query("MP3_320", description="Audio quality"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Download a track from Telegram via Telethon.
    Accepts either Spotify ID or Deezer ID (track_id).
    Quality is strictly forced to MP3_320.
    """
    quality = "MP3_320"
    try:
        track = None
        
        # Determine if this looks like a Spotify ID (alphanumeric with letters) or Deezer ID (numeric)
        is_spotify_id = not track_id.isdigit() and len(track_id) == 22
        
        if is_spotify_id:
            # Try to find by Spotify ID first
            query = select(Track).where(
                Track.spotify_id == str(track_id),
                Track.quality == quality
            )
            result = await db.execute(query)
            track = result.scalar_one_or_none()
        
        # If not found by Spotify ID (or it's a Deezer ID), try track_id
        if not track:
            query = select(Track).where(
                Track.track_id == str(track_id),
                Track.quality == quality
            )
            result = await db.execute(query)
            track = result.scalar_one_or_none()

        if not track:
            raise HTTPException(status_code=404, detail="Track not found or quality not available. Download the track first via the bot.")

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
