import uuid
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    BigInteger,
    ForeignKey,
    TIMESTAMP,
    Text,
    Enum,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database.session import Base


class User(Base):
    __tablename__ = "users"
    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    is_bot = Column(Boolean, default=False)
    language_code = Column(String(10), nullable=True)
    is_premium = Column(Boolean, default=False)
    added_to_attachment_menu = Column(Boolean, default=False)
    can_join_groups = Column(Boolean, default=True)
    can_read_all_group_messages = Column(Boolean, default=False)
    supports_inline_queries = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    last_activity = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    downloads = relationship("UserDownload", back_populates="user", cascade="all, delete-orphan")
    playlists = relationship("Playlist", back_populates="user", cascade="all, delete-orphan")


class UserSettings(Base):
    __tablename__ = "user_settings"
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    download_quality = Column(String(50), default="MP3_320")
    make_zip = Column(Boolean, default=True)
    language = Column(String(10), default="en")
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="settings")


class UserActivity(Base):
    __tablename__ = "user_activity"
    activity_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    activity_type = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="activities")


class Track(Base):
    __tablename__ = "tracks"
    track_id = Column(BigInteger, primary_key=True)
    url = Column(Text, nullable=False)
    file_id = Column(Text, nullable=True)
    title = Column(String(255), nullable=True)
    artist = Column(String(255), nullable=True)
    album = Column(String(255), nullable=True)
    duration = Column(Integer, nullable=True)
    download_count = Column(Integer, default=1)
    last_downloaded = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (Index("idx_tracks_downloads", download_count.desc()),)


class UserDownload(Base):
    __tablename__ = "user_downloads"
    download_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    deezer_id = Column(BigInteger, nullable=False)
    content_type = Column(String(20), nullable=False)
    file_id = Column(Text, nullable=False)
    quality = Column(String(50), nullable=False)
    url = Column(Text, nullable=True)
    title = Column(String(255), nullable=True)
    artist = Column(String(255), nullable=True)
    album = Column(String(255), nullable=True)
    duration = Column(Integer, nullable=True)
    file_name = Column(Text, nullable=True)
    downloaded_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="downloads")

    __table_args__ = (
        UniqueConstraint("user_id", "deezer_id", "content_type", name="user_content_unique"),
        Index("idx_downloads_user_id", "user_id"),
        Index("idx_downloads_timestamp", "downloaded_at"),
    )


class Playlist(Base):
    __tablename__ = "playlists"
    playlist_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="playlists")
    tracks = relationship("PlaylistTrack", back_populates="playlist", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("user_id", "name"),)


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"
    playlist_track_id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(Integer, ForeignKey("playlists.playlist_id", ondelete="CASCADE"))
    track_deezer_id = Column(BigInteger, nullable=False)
    added_at = Column(TIMESTAMP, server_default=func.now())

    playlist = relationship("Playlist", back_populates="tracks")
