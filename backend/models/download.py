from sqlalchemy import Column, BigInteger, String, Integer, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class UserDownload(Base):
    __tablename__ = "user_downloads"

    download_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    deezer_id = Column(BigInteger, nullable=False, index=True)
    content_type = Column(String(20), nullable=False)
    file_id = Column(Text, nullable=False)
    quality = Column(String(50), nullable=False)
    url = Column(Text, nullable=True)
    title = Column(String(255), nullable=True)
    artist = Column(String(255), nullable=True)
    album = Column(String(255), nullable=True)
    duration = Column(Integer, nullable=True)
    file_name = Column(Text, nullable=True)
    downloaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Unique constraint
    __table_args__ = (
        UniqueConstraint('user_id', 'deezer_id', 'content_type', name='user_content_unique'),
    )

    # Relationship
    user = relationship("User", back_populates="downloads")
