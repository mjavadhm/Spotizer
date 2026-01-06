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

    async def get_file_stream(self, message_id: int, channel_id: int):
        """
        Returns an async generator that yields chunks of the file from the given message.
        """
        if not self.client:
            raise Exception("Telegram client is not initialized.")

        if not self.client.is_connected():
            logger.warning("Telethon client not connected. Attempting to connect...")
            await self.client.connect()

        try:
            # Telethon allows getting messages by ID from a channel
            # channel_id from DB might be a negative number (standard for channels in Bot API)
            # Telethon usually handles IDs flexibly, but sometimes needs adjustments.
            # If the ID starts with -100, Telethon PeerChannel might need the positive part,
            # or we can pass the entity directly if we can resolve it.
            # Ideally, passing the raw integer ID works if the entity is cached or we use get_entity.

            # First, fetch the message to get the media
            message = await self.client.get_messages(channel_id, ids=message_id)

            if not message or not message.media:
                logger.error(f"Message {message_id} in channel {channel_id} not found or has no media.")
                return None

            # Create a generator using iter_download
            async def stream_generator():
                try:
                    async for chunk in self.client.iter_download(message.media, chunk_size=1024*1024): # 1MB chunks
                        yield chunk
                except Exception as e:
                    logger.error(f"Error during streaming: {e}")
                    raise

            return stream_generator()

        except Exception as e:
            logger.error(f"Error getting file stream: {e}")
            raise

# Global instance
telegram_service = TelegramService()
