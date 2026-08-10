# admin-backend/models/victim.py

from sqlalchemy import (
    Boolean,
    Column,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
import enum
from database import Base
from models.types import UTCDateTime, utc_now

class VictimStatus(enum.Enum):
    email_sent = "email_sent"
    email_opened = "email_opened"
    email_link_clicked = "email_link_clicked"
    data_submitted = "data_submitted"
    email_bounced = "email_bounced"
    pending = "pending"
    error = "error"

class Victim(Base):
    __tablename__ = 'victims'

    # Primary Key
    id = Column(String, primary_key=True)

    # Foreign Key
    campaign_id = Column(String, ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False, index=True)

    target_id = Column(String, ForeignKey('targets.id', ondelete='SET NULL'), nullable=True, index=True)

    # Contact information copied from the target.
    email = Column(String, nullable=False, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    position = Column(String, nullable=True)
    company = Column(String, nullable=True)

    # Tracking
    tracking_id = Column(String, unique=True, nullable=False, index=True)

    # Status
    status = Column(SQLEnum(VictimStatus), default=VictimStatus.email_sent, nullable=False, index=True)

    # Timeline
    scheduled_send_at = Column(UTCDateTime(), nullable=False)
    email_sent_at = Column(UTCDateTime(), nullable=True)
    email_opened_at = Column(UTCDateTime(), nullable=True)
    email_link_clicked_at = Column(UTCDateTime(), nullable=True)
    data_submitted_at = Column(UTCDateTime(), nullable=True)

    # Session Info (kept for backward compatibility)
    session_id = Column(String, unique=True, nullable=True, index=True)

    # Network info
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)

    # Browser and device information
    browser = Column(String, nullable=True)
    os = Column(String, nullable=True)
    device = Column(String, nullable=True)
    location = Column(String, nullable=True)  # GeoIP

    # Victim container information
    container_id = Column(String, nullable=True)
    container_name = Column(String, nullable=True)
    vnc_port = Column(Integer, nullable=True)
    vnc_password = Column(String, nullable=True)
    container_status = Column(String, nullable=True)

    # Timing
    first_seen = Column(UTCDateTime(), nullable=True, index=True)
    last_seen = Column(UTCDateTime(), nullable=True)
    session_duration_seconds = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=False, index=True)

    submitted_data = Column(JSON, nullable=True)

    created_at = Column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
        index=True,
    )

    # Metadata (JSON)
    extra_metadata = Column(JSON, nullable=True)

    # Relationships
    campaign = relationship("Campaign", back_populates="victims")
    target = relationship("Target", backref="victims")
    events = relationship("VictimEvent", back_populates="victim", cascade="all, delete-orphan")
    data_collections = relationship("DataCollection", back_populates="victim", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_victim_campaign', 'campaign_id'),
        Index('idx_victim_token', 'tracking_id'),
        Index('idx_victim_email', 'email'),
        Index('idx_victim_status', 'status'),
    )

    def to_dict(self, include_events=False, include_data_collections=False):
        data = {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "target_id": self.target_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "scheduled_send_at": self.scheduled_send_at.isoformat() if self.scheduled_send_at else None,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "position": self.position,
            "company": self.company,
            "tracking_id": self.tracking_id,
            "status": self.status.value,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "browser": self.browser,
            "os": self.os,
            "device": self.device,
            "location": self.location,
            "is_active": self.is_active,
            "email_sent_at": self.email_sent_at.isoformat() if self.email_sent_at else None,
            "email_opened_at": self.email_opened_at.isoformat() if self.email_opened_at else None,
            "email_link_clicked_at": self.email_link_clicked_at.isoformat() if self.email_link_clicked_at else None,
            "data_submitted_at": self.data_submitted_at.isoformat() if self.data_submitted_at else None,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "session_duration_seconds": self.session_duration_seconds,
            "container_id": self.container_id,
            "container_status": self.container_status,
            "vnc_port": self.vnc_port,
        }

        if self.submitted_data:
            data["submitted_data"] = self.submitted_data

        if self.extra_metadata:
            data["metadata"] = self.extra_metadata

        if include_events:
            data["events"] = [e.to_dict() for e in self.events]

        if include_data_collections:
            data["data_collections"] = [d.to_dict() for d in self.data_collections]

        return data

    def update_last_seen(self, db_session):
        """Update last seen timestamp"""
        now = utc_now()
        if self.first_seen is not None:
            self.session_duration_seconds = int(
                (now - self.first_seen).total_seconds()
            )
        self.last_seen = now
        db_session.commit()

    def __repr__(self):
        return f"<Victim {self.email} in campaign {self.campaign_id} ({self.status.value})>"
