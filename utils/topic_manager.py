"""Per-user forum topics for organizing downloads (artist/album/playlist)."""
import logging

from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select, delete

from database.session import async_session_maker
from models.base import UserTopic

logger = logging.getLogger(__name__)

async def get_topic_thread_id(user_id: int, topic_type: str, topic_key: str):
    """Return stored thread_id for this item, or None."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(UserTopic).where(
                UserTopic.user_id == user_id,
                UserTopic.topic_type == topic_type,
                UserTopic.topic_key == str(topic_key),
            )
        )
        row = result.scalars().first()
        return row.thread_id if row else None

async def remove_topic(user_id: int, topic_type: str, topic_key: str):
    """Delete a stale topic record (e.g. user deleted the topic)."""
    async with async_session_maker() as session:
        async with session.begin():
            await session.execute(
                delete(UserTopic).where(
                    UserTopic.user_id == user_id,
                    UserTopic.topic_type == topic_type,
                    UserTopic.topic_key == str(topic_key),
                )
            )

async def get_or_create_topic(bot, user_id: int, topic_type: str, topic_key: str, title: str):
    """Return (thread_id, created). thread_id is None if creation failed."""
    existing = await get_topic_thread_id(user_id, topic_type, topic_key)
    if existing:
        return existing, False

    try:
        topic = await bot.create_forum_topic(chat_id=user_id, name=str(title)[:128])
        thread_id = topic.message_thread_id
    except Exception as e:
        logger.warning("Could not create topic for user %s: %s", user_id, e)
        return None, False

    async with async_session_maker() as session:
        async with session.begin():
            session.add(UserTopic(
                user_id=user_id,
                topic_type=topic_type,
                topic_key=str(topic_key),
                title=str(title)[:255],
                thread_id=thread_id,
            ))
    return thread_id, True

async def send_safely(send_func, user_id: int, topic_type: str, topic_key: str, thread_id, **kwargs):
    """Send a message into a topic; on failure fall back to main chat and clean up.

    send_func: a bound bot method like bot.send_audio / bot.send_document / bot.send_message
    kwargs: all original arguments of that call (chat_id, document, caption, ...)
    """
    if thread_id:
        try:
            return await send_func(message_thread_id=thread_id, **kwargs)
        except TelegramBadRequest as e:
            logger.warning("Topic send failed (%s); falling back to main chat", e)
            await remove_topic(user_id, topic_type, topic_key)
    return await send_func(**kwargs)
