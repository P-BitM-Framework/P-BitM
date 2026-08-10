from __future__ import annotations

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from database import Base
from models.types import UTCDateTime, utc_now


class UserSession(Base):
    __tablename__ = "user_sessions"

    token_hash = Column(String(64), primary_key=True)
    user_id = Column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    csrf_hash = Column(String(64), nullable=False)
    created_at = Column(
        UTCDateTime(),
        nullable=False,
        default=utc_now,
    )
    expires_at = Column(UTCDateTime(), nullable=False, index=True)
    last_seen_at = Column(UTCDateTime(), nullable=False)
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(64), nullable=True)

    user = relationship("User", back_populates="sessions")
