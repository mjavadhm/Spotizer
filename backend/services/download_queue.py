"""
Download Queue Service

Background download queue with priority support and rate limiting.
Handles pre-downloading tracks on search/browse and on-demand downloads for streaming.
"""
import asyncio
import os
import logging
from asyncio import PriorityQueue
from dataclasses import dataclass, field
from typing import Optional, Dict, Set
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import AsyncSessionLocal as async_session_maker
from ..models.download_queue import DownloadQueueItem
from ..models.track import Track
from .telegram_client import telegram_service

logger = logging.getLogger(__name__)


@dataclass(order=True)
class QueueItem:
    """Priority queue item wrapper."""
    priority: int
    spotify_id: str = field(compare=False)
    title: str = field(compare=False, default="")
    artist: str = field(compare=False, default="")
    db_id: Optional[int] = field(compare=False, default=None)
    event: Optional[asyncio.Event] = field(compare=False, default=None)


class DownloadQueue:
    """
    Background download queue with priority support.
    
    Priority levels:
    - 1: HIGH (on-demand, user waiting)
    - 10: LOW (pre-download, background)
    """
    
    PRIORITY_HIGH = 1
    PRIORITY_LOW = 10
    RATE_LIMIT_SECONDS = 10  # Delay between downloads
    
    def __init__(self):
        self.queue: PriorityQueue = PriorityQueue()
        self.processing: Set[str] = set()  # Track spotify_ids being processed
        self.pending_events: Dict[str, asyncio.Event] = {}  # For blocking waits
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False
        self._deezer_service = None
        
    def _get_deezer_service(self):
        """Lazy load DeezerService to avoid circular imports."""
        if self._deezer_service is None:
            from .deezer_service import DeezerService
            self._deezer_service = DeezerService()
        return self._deezer_service
    
    async def start(self):
        """Start the queue worker."""
        if self._running:
            return
        
        self._running = True
        
        # Load pending items from database
        await self._load_pending_from_db()
        
        # Start worker task
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("Download queue worker started")
    
    async def stop(self):
        """Stop the queue worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Download queue worker stopped")
    
    async def _load_pending_from_db(self):
        """Load pending items from database on startup."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(DownloadQueueItem)
                .where(DownloadQueueItem.status.in_(['pending', 'processing']))
                .order_by(DownloadQueueItem.priority, DownloadQueueItem.created_at)
            )
            items = result.scalars().all()
            
            for item in items:
                queue_item = QueueItem(
                    priority=item.priority,
                    spotify_id=item.spotify_id,
                    title=item.title or "",
                    artist=item.artist or "",
                    db_id=item.id
                )
                await self.queue.put(queue_item)
            
            if items:
                logger.info(f"Loaded {len(items)} pending items from database")
    
    async def add(
        self, 
        spotify_id: str, 
        title: str = "", 
        artist: str = "",
        priority: int = PRIORITY_LOW
    ) -> bool:
        """
        Add a track to the download queue.
        
        Returns True if added, False if already exists/queued.
        """
        # Skip if already processing or in queue
        if spotify_id in self.processing:
            return False
        
        # Check if already downloaded
        async with async_session_maker() as session:
            # Check by spotify_id
            result = await session.execute(
                select(Track).where(Track.spotify_id == spotify_id)
            )
            if result.scalar_one_or_none():
                return False  # Already downloaded
            
            # Check if already in queue
            result = await session.execute(
                select(DownloadQueueItem).where(
                    DownloadQueueItem.spotify_id == spotify_id,
                    DownloadQueueItem.status.in_(['pending', 'processing'])
                )
            )
            if result.scalar_one_or_none():
                return False  # Already queued
            
            # Add to database
            db_item = DownloadQueueItem(
                spotify_id=spotify_id,
                title=title,
                artist=artist,
                priority=priority,
                status='pending'
            )
            session.add(db_item)
            await session.commit()
            await session.refresh(db_item)
            
            # Add to memory queue
            queue_item = QueueItem(
                priority=priority,
                spotify_id=spotify_id,
                title=title,
                artist=artist,
                db_id=db_item.id
            )
            await self.queue.put(queue_item)
            
            logger.info(f"Added to queue: {title} - {artist} (priority={priority})")
            return True
    
    async def add_batch(
        self, 
        tracks: list, 
        priority: int = PRIORITY_LOW,
        max_items: int = 20
    ):
        """
        Add multiple tracks to the queue.
        
        Args:
            tracks: List of dicts with 'id', 'name', 'artists' (Spotify format)
            priority: Priority level
            max_items: Maximum items to add (for large playlists)
        """
        added = 0
        for track in tracks[:max_items]:
            spotify_id = track.get('id')
            if not spotify_id:
                continue
            
            title = track.get('name', '')
            artists = track.get('artists', [])
            artist = artists[0].get('name', '') if artists else ''
            
            if await self.add(spotify_id, title, artist, priority):
                added += 1
        
        if added:
            logger.info(f"Added {added} tracks to queue (batch)")
        
        return added
    
    async def add_high_priority(
        self, 
        spotify_id: str, 
        title: str = "", 
        artist: str = ""
    ) -> asyncio.Event:
        """
        Add a track with high priority and return an event to wait on.
        Used for on-demand downloads when user clicks stream.
        
        Returns an asyncio.Event that will be set when download completes.
        """
        # Check if already downloaded
        async with async_session_maker() as session:
            result = await session.execute(
                select(Track).where(Track.spotify_id == spotify_id)
            )
            track = result.scalar_one_or_none()
            if track and track.message_id and track.channel_id:
                # Already available, return immediately
                event = asyncio.Event()
                event.set()
                return event
        
        # Create event for waiting
        event = asyncio.Event()
        self.pending_events[spotify_id] = event
        
        # Add to database and queue with high priority
        async with async_session_maker() as session:
            # Check if already in queue - update priority if so
            result = await session.execute(
                select(DownloadQueueItem).where(
                    DownloadQueueItem.spotify_id == spotify_id,
                    DownloadQueueItem.status.in_(['pending', 'processing'])
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update to high priority
                existing.priority = self.PRIORITY_HIGH
                await session.commit()
            else:
                # Add new with high priority
                db_item = DownloadQueueItem(
                    spotify_id=spotify_id,
                    title=title,
                    artist=artist,
                    priority=self.PRIORITY_HIGH,
                    status='pending'
                )
                session.add(db_item)
                await session.commit()
                await session.refresh(db_item)
                
                # Add to memory queue
                queue_item = QueueItem(
                    priority=self.PRIORITY_HIGH,
                    spotify_id=spotify_id,
                    title=title,
                    artist=artist,
                    db_id=db_item.id,
                    event=event
                )
                await self.queue.put(queue_item)
        
        logger.info(f"Added high-priority download: {title} - {artist}")
        return event
    
    async def _worker(self):
        """Background worker that processes the queue."""
        logger.info("Download queue worker running")
        
        while self._running:
            try:
                # Wait for item with timeout
                try:
                    item: QueueItem = await asyncio.wait_for(
                        self.queue.get(), 
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the item
                self.processing.add(item.spotify_id)
                
                try:
                    await self._process_item(item)
                except Exception as e:
                    logger.error(f"Error processing {item.spotify_id}: {e}", exc_info=True)
                    await self._update_status(item.db_id, 'failed', str(e))
                finally:
                    self.processing.discard(item.spotify_id)
                    
                    # Signal completion if there's a waiting event
                    if item.spotify_id in self.pending_events:
                        self.pending_events[item.spotify_id].set()
                        del self.pending_events[item.spotify_id]
                
                # Rate limit (skip for high priority)
                if item.priority > self.PRIORITY_HIGH:
                    await asyncio.sleep(self.RATE_LIMIT_SECONDS)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def _process_item(self, item: QueueItem):
        """Process a single queue item."""
        logger.info(f"Processing: {item.title} - {item.artist} (spotify_id={item.spotify_id})")
        
        await self._update_status(item.db_id, 'processing')
        
        deezer_service = self._get_deezer_service()
        
        # Step 1: Convert Spotify ID to Deezer URL
        spotify_url = f"https://open.spotify.com/track/{item.spotify_id}"
        deezer_url = await deezer_service.convert_to_deezer(spotify_url)
        
        if not deezer_url:
            raise Exception("Failed to convert Spotify ID to Deezer URL")
        
        # Extract Deezer ID
        content_type, deezer_id = deezer_service.extract_info_from_url(deezer_url)
        
        if not deezer_id:
            raise Exception("Failed to extract Deezer ID")
        
        # Step 2: Check if we already have this track by Deezer ID
        async with async_session_maker() as session:
            result = await session.execute(
                select(Track).where(Track.track_id == str(deezer_id))
            )
            existing_track = result.scalar_one_or_none()
            
            if existing_track:
                # Track exists! Just update spotify_id
                existing_track.spotify_id = item.spotify_id
                await session.commit()
                logger.info(f"Updated existing track with spotify_id: {deezer_id} -> {item.spotify_id}")
                await self._update_status(item.db_id, 'done')
                return
        
        # Step 3: Download and upload to channel
        await self._download_and_upload(
            item.spotify_id,
            deezer_url,
            str(deezer_id),
            item.title,
            item.artist,
            item.db_id
        )
    
    async def _download_and_upload(
        self,
        spotify_id: str,
        deezer_url: str,
        deezer_id: str,
        title: str,
        artist: str,
        db_id: Optional[int]
    ):
        """Download track from Deezer and upload to Telegram channel."""
        deezer_service = self._get_deezer_service()
        
        # Download from Deezer
        quality = os.getenv('DEFAULT_QUALITY', 'MP3_320')
        smart = await deezer_service.download(deezer_url, quality_download=quality)
        
        if not smart or not hasattr(smart, 'track') or not smart.track:
            raise Exception("Failed to download track from Deezer")
        
        file_path = smart.track.song_path
        
        try:
            # Get metadata
            track_title = smart.track.music if hasattr(smart.track, 'music') else title
            track_artist = smart.track.artist if hasattr(smart.track, 'artist') else artist
            track_album = smart.track.album if hasattr(smart.track, 'album') else ""
            
            # Upload to Telegram channel
            music_channel_id = os.getenv('MUSIC_CHANNEL_ID')
            if not music_channel_id:
                raise Exception("MUSIC_CHANNEL_ID not configured")
            
            channel_id, message_id, file_id = await telegram_service.upload_audio(
                file_path=file_path,
                channel_id=int(music_channel_id),
                title=track_title,
                artist=track_artist,
                caption=f"@Spotizer_bot 🎧"
            )
            
            # Get audio duration
            from ..utils.file_handler import get_audio_duration
            duration = get_audio_duration(file_path)
            
            # Save to database
            async with async_session_maker() as session:
                track = Track(
                    track_id=deezer_id,
                    spotify_id=spotify_id,
                    url=deezer_url,
                    file_id=file_id,
                    title=track_title,
                    artist=track_artist,
                    album=track_album,
                    quality=quality,
                    duration=duration,
                    channel_id=channel_id,
                    message_id=message_id
                )
                session.add(track)
                await session.commit()
            
            logger.info(f"Downloaded and uploaded: {track_title} - {track_artist}")
            await self._update_status(db_id, 'done')
            
        finally:
            # Cleanup file
            if os.path.exists(file_path):
                os.remove(file_path)
    
    async def _update_status(
        self, 
        db_id: Optional[int], 
        status: str, 
        error_message: str = None
    ):
        """Update queue item status in database."""
        if not db_id:
            return
        
        async with async_session_maker() as session:
            stmt = (
                update(DownloadQueueItem)
                .where(DownloadQueueItem.id == db_id)
                .values(status=status, error_message=error_message)
            )
            await session.execute(stmt)
            await session.commit()


# Global instance
download_queue = DownloadQueue()
