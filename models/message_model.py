import aiogram
from typing import Dict, Optional, Any
from datetime import datetime
from database.connection import get_connection
from logger import get_logger

logger = get_logger(__name__)

class MessageModel:
    def add_message(self, user_id: int, message: aiogram.types.Message) -> bool:
        """
        Extract data from aiogram Message and insert it into messages table
        
        Args:
            user_id: User's telegram ID
            message: aiogram Message object
        
        Returns:
            bool: True if insertion was successful, False otherwise
        """
        try:
            # Extract message data
            message_id = message.message_id
            message_text = message.text or message.caption or ""
            sent_at = message.date
            
            # Determine message type and media content
            if message.content_type == "text":
                message_type = "text"
                media = None
            elif message.content_type == "photo":
                message_type = "photo"
                # Get file_id of the largest photo
                photo_sizes = message.photo
                media = photo_sizes[-1].file_id if photo_sizes else None
            elif message.content_type == "document":
                message_type = "document"
                media = message.document.file_id if message.document else None
            elif message.content_type == "audio":
                message_type = "audio"
                media = message.audio.file_id if message.audio else None
            elif message.content_type == "video":
                message_type = "video"
                media = message.video.file_id if message.video else None
            elif message.content_type == "voice":
                message_type = "voice"
                media = message.voice.file_id if message.voice else None
            else:
                message_type = message.content_type
                media = None
            
            if user_id == message.from_user.id:
                sent_by = 0
            else:
                sent_by = 1
            # Get database connection
            conn = get_connection()
            cursor = conn.cursor()
            
            # Insert into messages table
            query = """
            INSERT INTO messages (message_id, user_id, message_text, message_type, sent_at, sent_by, media)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(
                query, 
                (message_id, user_id, message_text, message_type, sent_at, sent_by, media)
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Added message {message_id} from user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return False