import asyncio
import logging
import os
from telethon import TelegramClient
from ..config import settings

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.client = None
        if settings.API_ID and settings.API_HASH:
            # Ensure the session directory exists
            session_path = os.path.dirname(settings.SESSION_NAME)
            if session_path and not os.path.exists(session_path):
                os.makedirs(session_path)

            self.client = TelegramClient(
                settings.SESSION_NAME,
                settings.API_ID,
                settings.API_HASH
            )
        else:
            logger.warning("Telethon API_ID or API_HASH not set. TelegramService disabled.")

    async def start(self):
        """Start the Telethon client"""
        if self.client:
            try:
                logger.info("Starting Telethon client...")
                await self.client.start()
                logger.info("Telethon client started successfully.")
            except Exception as e:
                logger.error(f"Failed to start Telethon client: {e}")
                # We don't raise here to allow the app to start even if Telethon fails (optional)

    async def stop(self):
        """Stop the Telethon client"""
        if self.client:
            try:
                logger.info("Disconnecting Telethon client...")
                await self.client.disconnect()
                logger.info("Telethon client disconnected.")
            except Exception as e:
                logger.error(f"Error disconnecting Telethon client: {e}")

    async def get_file_info(self, message_id: int, channel_id: int):
        """
        Get file information (size, etc.) from a Telegram message.
        Returns (message, file_size) tuple or (None, 0) if not found.
        """
        if not self.client:
            raise Exception("Telegram client is not initialized.")

        if not self.client.is_connected():
            logger.warning("Telethon client not connected. Attempting to connect...")
            await self.client.connect()

        try:
            message = await self.client.get_messages(channel_id, ids=message_id)

            if not message or not message.media:
                logger.error(f"Message {message_id} in channel {channel_id} not found or has no media.")
                return None, 0

            # Get file size from media
            file_size = 0
            if hasattr(message.media, 'document'):
                file_size = message.media.document.size
            elif hasattr(message, 'file') and message.file:
                file_size = message.file.size or 0

            return message, file_size

        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            raise

    async def get_file_stream(self, message_id: int, channel_id: int, offset: int = 0, limit: int = None):
        """
        Returns an async generator that yields chunks of the file from the given message.
        
        Args:
            message_id: Telegram message ID
            channel_id: Telegram channel ID
            offset: Byte offset to start streaming from (for Range requests)
            limit: Maximum bytes to stream (for Range requests), None for entire file
        """
        if not self.client:
            raise Exception("Telegram client is not initialized.")

        if not self.client.is_connected():
            logger.warning("Telethon client not connected. Attempting to connect...")
            await self.client.connect()

        try:
            message = await self.client.get_messages(channel_id, ids=message_id)

            if not message or not message.media:
                logger.error(f"Message {message_id} in channel {channel_id} not found or has no media.")
                return None

            # Create a generator using iter_download with offset support
            async def stream_generator():
                bytes_sent = 0
                try:
                    async for chunk in self.client.iter_download(
                        message.media, 
                        chunk_size=1024*1024,  # 1MB chunks
                        offset=offset
                    ):
                        if limit is not None:
                            remaining = limit - bytes_sent
                            if remaining <= 0:
                                break
                            if len(chunk) > remaining:
                                chunk = chunk[:remaining]
                        
                        bytes_sent += len(chunk)
                        yield chunk
                        
                        if limit is not None and bytes_sent >= limit:
                            break
                            
                except Exception as e:
                    logger.error(f"Error during streaming: {e}")
                    raise

            return stream_generator()

        except Exception as e:
            logger.error(f"Error getting file stream: {e}")
            raise

    async def upload_audio(
        self, 
        file_path: str, 
        channel_id: int, 
        title: str = "", 
        artist: str = "",
        caption: str = ""
    ) -> tuple[int, int, str]:
        """
        Upload an audio file to a Telegram channel.
        
        Args:
            file_path: Path to the audio file
            channel_id: Telegram channel ID to upload to
            title: Audio title for metadata
            artist: Artist name for metadata
            caption: Message caption
            
        Returns:
            Tuple of (channel_id, message_id, file_id)
        """
        if not self.client:
            raise Exception("Telegram client is not initialized.")

        if not self.client.is_connected():
            logger.warning("Telethon client not connected. Attempting to connect...")
            await self.client.connect()

        try:
            logger.info(f"Uploading audio to channel {channel_id}: {title} - {artist}")
            
            # Send the file to the channel
            message = await self.client.send_file(
                channel_id,
                file_path,
                caption=caption,
                attributes=[
                    # Add audio attributes for proper display
                    # DocumentAttributeAudio is imported dynamically to avoid issues
                ]
            )
            
            if not message:
                raise Exception("Failed to send file to channel")
            
            # Get file_id from the sent message
            file_id = ""
            if message.audio:
                file_id = str(message.audio.id)
            elif message.document:
                file_id = str(message.document.id)
            
            logger.info(f"Uploaded audio: msg_id={message.id}, file_id={file_id}")
            
            return channel_id, message.id, file_id

        except Exception as e:
            logger.error(f"Error uploading audio: {e}")
            raise

# Global instance
telegram_service = TelegramService()
