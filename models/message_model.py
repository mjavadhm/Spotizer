import aiogram
from sqlalchemy.future import select
from database.session import async_session_maker
from models.base import Message
from logger import get_logger

logger = get_logger(__name__)

class MessageModel:
    @staticmethod
    async def add_message(user_id: int, message: aiogram.types.Message) -> bool:
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
            sent_at = message.date.replace(tzinfo=None)
            
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
            
            async with async_session_maker() as session:
                async with session.begin():
                    new_message = Message(
                        message_id=message_id,
                        user_id=user_id,
                        message_text=message_text,
                        message_type=message_type,
                        sent_at=sent_at,
                        sent_by=sent_by,
                        media=media,
                    )
                    session.add(new_message)
                await session.commit()
                logger.info(f"Added message {message_id} from user {user_id}")
                return True
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return False
