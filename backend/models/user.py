from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String(255), nullable=True)
    # Note: email and hashed_password removed - this is a Telegram-only auth system
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    is_bot = Column(Boolean, default=False)
    language_code = Column(String(10), nullable=True)
    is_premium = Column(Boolean, default=False)
    added_to_attachment_menu = Column(Boolean, default=False)
    can_join_groups = Column(Boolean, default=True)
    can_read_all_group_messages = Column(Boolean, default=False)
    supports_inline_queries = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
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
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="settings")


class UserActivity(Base):
    __tablename__ = "user_activity"

    activity_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    activity_type = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    user = relationship("User", back_populates="activities")
