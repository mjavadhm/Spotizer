from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from models.download_model import DownloadModel
from backend.services.telegram_client import telegram_service
import logging

router = APIRouter(tags=["Stream"])
logger = logging.getLogger(__name__)

# Re-use download model from bot.
# Note: In a larger app, we might want a separate service layer in backend/services
# but here we reuse the existing model which uses the same DB.
download_model = DownloadModel()

@router.get("/stream/{track_id}")
async def stream_track(
    track_id: int,
    quality: str = Query("MP3_320", description="Audio quality")
):
    """
    Stream a track from Telegram via Telethon.
    """
    try:
        # 1. Lookup track in DB
        # User ID is required by the model method but for public streaming/by ID we might not need a specific user.
        # However, the method signature is `get_track_by_deezer_id_quality(self, user_id, deezer_id, quality)`
        # The implementation in DownloadModel ignores user_id for the SELECT query on `tracks` table.
        # It only uses user_id for `user_downloads` table lookups which we aren't using here.
        # Wait, let's verify `get_track_by_deezer_id_quality` implementation.
        # It does: `SELECT ... FROM tracks WHERE track_id = %s AND quality = %s`
        # It does NOT filter by user_id. So passing 0 or any dummy ID is fine.

        track_info = download_model.get_track_by_deezer_id_quality(0, track_id, quality)

        if not track_info:
            raise HTTPException(status_code=404, detail="Track not found or quality not available")

        message_id = track_info.get('message_id')
        channel_id = track_info.get('channel_id')

        if not message_id or not channel_id:
             raise HTTPException(status_code=404, detail="Track source not available (message_id/channel_id missing)")

        # 2. Get stream generator from Telethon
        file_iterator = await telegram_service.get_file_stream(message_id, channel_id)

        if not file_iterator:
            raise HTTPException(status_code=404, detail="File content not found in Telegram")

        # 3. Return StreamingResponse
        # Determine media type based on quality or filename extension
        media_type = "audio/mpeg" # Default to MP3
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
    quality: str = Query("MP3_320", description="Audio quality")
):
    """
    Download a track from Telegram via Telethon.
    """
    try:
        track_info = download_model.get_track_by_deezer_id_quality(0, track_id, quality)

        if not track_info:
            raise HTTPException(status_code=404, detail="Track not found or quality not available")

        message_id = track_info.get('message_id')
        channel_id = track_info.get('channel_id')
        file_name = track_info.get('file_name', f"track_{track_id}.mp3")

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
