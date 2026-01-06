from sqlalchemy import Column, BigInteger, String, Integer, DateTime, Text
from sqlalchemy.sql import func
from ..database import Base


class Track(Base):
    __tablename__ = "tracks"

    track_id = Column(BigInteger, primary_key=True, index=True)
    content_type = Column(String(20), default="track")
    url = Column(Text, nullable=False)
    file_id = Column(Text, nullable=True)
    title = Column(String(255), nullable=True)
    artist = Column(String(255), nullable=True)
    album = Column(String(255), nullable=True)
    duration = Column(Integer, nullable=True)
    quality = Column(String(50), nullable=True)
    file_name = Column(Text, nullable=True)
    download_count = Column(Integer, default=1)
    last_downloaded = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Telegram message reference for streaming
    channel_id = Column(BigInteger, nullable=True)
    message_id = Column(BigInteger, nullable=True)
