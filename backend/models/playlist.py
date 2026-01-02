from sqlalchemy import Column, BigInteger, Integer, String, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from ..database import Base


class Playlist(Base):
    __tablename__ = "playlists"

    playlist_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='user_playlist_name_unique'),
    )

    # Relationships
    user = relationship("User", back_populates="playlists")
    tracks = relationship("PlaylistTrack", back_populates="playlist", cascade="all, delete-orphan")


class PlaylistTrack(Base):
    __tablename__ = "playlist_tracks"

    playlist_track_id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(Integer, ForeignKey("playlists.playlist_id", ondelete="CASCADE"), index=True)
    track_deezer_id = Column(BigInteger, nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    playlist = relationship("Playlist", back_populates="tracks")
