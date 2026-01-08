import uuid
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    BigInteger,
    ForeignKey,
    TIMESTAMP,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from bale_bot.database import BaleBase


class BaleUser(BaleBase):
    """User model for Bale bot - separate from Telegram users"""
    __tablename__ = "bale_users"
    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    is_bot = Column(Boolean, default=False)
    language_code = Column(String(10), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    last_activity = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    settings = relationship("BaleUserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    downloads = relationship("BaleUserDownload", back_populates="user", cascade="all, delete-orphan")
    playlists = relationship("BalePlaylist", back_populates="user", cascade="all, delete-orphan")


class BaleUserSettings(BaleBase):
    """User settings for Bale bot"""
    __tablename__ = "bale_user_settings"
    user_id = Column(BigInteger, ForeignKey("bale_users.user_id", ondelete="CASCADE"), primary_key=True)
    download_quality = Column(String(50), default="MP3_320")
    make_zip = Column(Boolean, default=True)
    language = Column(String(10), default="en")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("BaleUser", back_populates="settings")


class BaleUserDownload(BaleBase):
    """Download history for Bale bot - no file_id caching"""
    __tablename__ = "bale_user_downloads"
    download_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("bale_users.user_id", ondelete="CASCADE"))
    deezer_id = Column(BigInteger, nullable=False)
    content_type = Column(String(20), nullable=False)
    quality = Column(String(50), nullable=False)
    url = Column(Text, nullable=True)
    title = Column(String(255), nullable=True)
    artist = Column(String(255), nullable=True)
    album = Column(String(255), nullable=True)
    duration = Column(Integer, nullable=True)
    file_name = Column(Text, nullable=True)
    downloaded_at = Column(TIMESTAMP, server_default=func.now())
    user_rating = Column(Integer, nullable=True)  # 1=like, -1=dislike, NULL=no rating

    user = relationship("BaleUser", back_populates="downloads")

    __table_args__ = (
        UniqueConstraint("user_id", "deezer_id", "content_type", "quality", name="bale_user_content_unique"),
        Index("idx_bale_downloads_user_id", "user_id"),
        Index("idx_bale_downloads_timestamp", "downloaded_at"),
    )


class BalePlaylist(BaleBase):
    """Playlist model for Bale bot"""
    __tablename__ = "bale_playlists"
    playlist_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("bale_users.user_id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("BaleUser", back_populates="playlists")
    tracks = relationship("BalePlaylistTrack", back_populates="playlist", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("user_id", "name"),)


class BalePlaylistTrack(BaleBase):
    """Playlist track model for Bale bot"""
    __tablename__ = "bale_playlist_tracks"
    playlist_track_id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(Integer, ForeignKey("bale_playlists.playlist_id", ondelete="CASCADE"))
    track_deezer_id = Column(BigInteger, nullable=False)
    added_at = Column(TIMESTAMP, server_default=func.now())

    playlist = relationship("BalePlaylist", back_populates="tracks")
