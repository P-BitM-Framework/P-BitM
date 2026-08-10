# admin-backend/models/victim_event.py

import enum
import uuid
from sqlalchemy import (
    Column,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database import Base
from models.types import UTCDateTime, utc_now

class EventType(str, enum.Enum):
    # Email events
    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    EMAIL_LINK_CLICKED = "email_link_clicked"
    EMAIL_BOUNCED = "email_bounced"
    EMAIL_MARKED_SPAM = "email_marked_spam"

    # Victim engagement
    VICTIM_CONNECTED = "victim_connected"
    VICTIM_DISCONNECTED = "victim_disconnected"

    # Browser activity
    NAVIGATION = "navigation"
    FORM_SUBMISSION = "form_submission"
    COOKIE_CAPTURED = "cookie_captured"

    # File activity
    FILE_DOWNLOADED = "file_downloaded"
    FILE_UPLOADED = "file_uploaded"

    # Screenshots/Recordings
    SCREENSHOT = "screenshot"
    KEYLOG = "keylog"

    # Suspicious behavior
    COPY_PASTE = "copy_paste"
    DEVELOPER_TOOLS_OPENED = "developer_tools_opened"

class VictimEvent(Base):
    __tablename__ = "victim_events"

    # Primary Key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    victim_id = Column(String, ForeignKey("victims.id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(String, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)

    # Event Details
    event_type = Column(SQLEnum(EventType), nullable=False, index=True)
    timestamp = Column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
        index=True,
    )

    # Event-specific data
    title = Column(String, nullable=True)        # "Screenshot captured", "Navigated to new page"
    description = Column(Text, nullable=True)    # URL, details, etc.
    url = Column(String, nullable=True)          # URL involved in the event (if applicable)
    hostname = Column(String, nullable=True)     # Hostname for navigation events, etc.

    # Metadata (JSON)
    payload = Column(JSON, nullable=True)

    # Relationships
    victim = relationship("Victim", back_populates="events")
    campaign = relationship("Campaign", back_populates="events")

    # Indexes
    __table_args__ = (
        Index('idx_event_victim', 'victim_id'),
        Index('idx_event_campaign', 'campaign_id'),
        Index('idx_event_type', 'event_type'),
        Index('idx_event_timestamp', 'timestamp'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "victim_id": self.victim_id,
            "campaign_id": self.campaign_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "url": self.url,
            "hostname": self.hostname,
            "title": self.title,
            "description": self.description,
            "payload": self.payload if isinstance(self.payload, dict) else {},
        }

    def __repr__(self):
        return f"<VictimEvent {self.event_type.value} at {self.timestamp}>"
