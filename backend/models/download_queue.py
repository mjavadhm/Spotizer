from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from ..database import Base


class DownloadQueueItem(Base):
    """Model for tracking download queue items in the database."""
    __tablename__ = "download_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    spotify_id = Column(String(64), nullable=True, index=True)
    deezer_id = Column(String(64), nullable=True)
    title = Column(String(255), nullable=True)
    artist = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default='pending')  # pending, processing, done, failed
    priority = Column(Integer, nullable=False, default=10)  # 1 = high (on-demand), 10 = low (pre-download)
    error_message = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
