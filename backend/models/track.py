from sqlalchemy import Column, BigInteger, String, Integer, DateTime, Text
from sqlalchemy.sql import func
from ..database import Base


class Track(Base):
    __tablename__ = "tracks"

    # Match exact database schema
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    track_id = Column(String(64), index=True)  # Deezer track ID as string
    url = Column(Text, nullable=True)
    file_id = Column(Text, nullable=True)
    title = Column(String(255), nullable=True)
    artist = Column(String(255), nullable=True)
    album = Column(String(255), nullable=True)
    duration = Column(Integer, nullable=True)
    download_count = Column(Integer, default=1)
    last_downloaded = Column(DateTime, server_default=func.now())
    quality = Column(String(16), nullable=True)
    file_name = Column(Text, nullable=True)
    content_type = Column(String(64), default="track")
    telethon_file_id = Column(Text, nullable=True)
    # Telegram message reference for streaming
    channel_id = Column(BigInteger, nullable=True)
    message_id = Column(BigInteger, nullable=True)
