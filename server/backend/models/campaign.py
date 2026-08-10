# admin-backend/models/campaign.py

from sqlalchemy import (
    Column,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
    or_,
)
from sqlalchemy.orm import relationship
import enum
from database import Base
from models.types import UTCDateTime, utc_now

class CampaignStatus(enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    active = "active"
    paused = "paused"
    completed = "completed"
    error = "error"

class Campaign(Base):
    __tablename__ = 'campaigns'

    # Primary Key
    id = Column(String, primary_key=True)

    # Basic Info
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.draft, nullable=False, index=True)
    campaign_type = Column(String, default="full", nullable=False)

    # Foreign keys
    target_list_id = Column(String, ForeignKey("target_lists.id", ondelete="RESTRICT"), nullable=True, index=True)
    email_template_id = Column(String, ForeignKey("email_templates.id", ondelete="RESTRICT"), nullable=True, index=True)
    sending_profile_id = Column(String, ForeignKey("sending_profiles.id", ondelete="RESTRICT"), nullable=True, index=True)
    landing_page_id = Column(String, ForeignKey("landing_pages.id", ondelete="RESTRICT"), nullable=True, index=True)

    # Target URL used by the landing page and victim container
    target_url = Column(String, nullable=False)

    # Browser mode
    mode = Column(String, default='kiosk')  # kiosk, normal, private
    protocol = Column(String, default='selkies')  # selkies, vnc

    # Container info (campaign container)
    container_id = Column(String, unique=True, nullable=True)
    container_name = Column(String, unique=True, nullable=True)
    container_status = Column(String, nullable=True)  # running, stopped, error

    # Network config
    host_ip = Column(String, nullable=True)
    host_port = Column(Integer, nullable=True)
    public_url = Column(String, nullable=True)

    # Extensions and runtime configuration
    plugin_ids = Column(JSON, default=list, nullable=False)
    module_ids = Column(JSON, default=list, nullable=False)
    selkies_config = Column(JSON, default=dict, nullable=False)
    advanced_options = Column(JSON, default=dict, nullable=False)

    # Scheduling
    scheduled_start = Column(UTCDateTime(), nullable=True)
    scheduled_end = Column(UTCDateTime(), nullable=True)
    started_at = Column(UTCDateTime(), nullable=True)
    completed_at = Column(UTCDateTime(), nullable=True)

    # Email statistics
    total_targets = Column(Integer, default=0, nullable=False)
    emails_sent = Column(Integer, default=0, nullable=False)
    emails_opened = Column(Integer, default=0, nullable=False)
    links_clicked = Column(Integer, default=0, nullable=False)
    data_submitted = Column(Integer, default=0, nullable=False)

    # Runtime statistics
    victims_count = Column(Integer, default=0)
    total_screenshots = Column(Integer, default=0)

    # Metadata
    created_by = Column(String, ForeignKey('users.id'), nullable=True, index=True)
    created_at = Column(UTCDateTime(), default=utc_now, nullable=False, index=True)
    updated_at = Column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    deleted_at = Column(UTCDateTime(), nullable=True)

    # Relationships
    target_list = relationship("TargetList", back_populates="campaigns")
    email_template = relationship("EmailTemplate", back_populates="campaigns")
    sending_profile = relationship("SMTPProfile", back_populates="campaigns")
    landing_page = relationship("LandingPage", back_populates="campaigns")

    creator = relationship("User", back_populates="campaigns", foreign_keys=[created_by])
    victims = relationship("Victim", back_populates="campaign", cascade="all, delete-orphan")
    events = relationship("VictimEvent", back_populates="campaign", cascade="all, delete-orphan")
    data_collections = relationship("DataCollection", back_populates="campaign", cascade="all, delete-orphan")

    def to_dict(self, include_victims=False, include_stats=True):
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "campaign_type": self.campaign_type,
            "target_url": self.target_url,
            "landing_page": self.landing_page.to_dict() if self.landing_page else None,
            "mode": self.mode,
            "protocol": self.protocol,
            "container_id": self.container_id,
            "container_name": self.container_name,
            "container_status": self.container_status,
            "host_ip": self.host_ip,
            "host_port": self.host_port,
            "public_url": self.public_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "scheduled_start": self.scheduled_start.isoformat() if self.scheduled_start else None,
            "scheduled_end": self.scheduled_end.isoformat() if self.scheduled_end else None,
            "from_email": self.sending_profile.from_email if self.sending_profile else None,
        }

        if include_stats:
            data.update({
                "total_targets": self.target_list.total_targets if self.target_list else self.total_targets,
                "emails_sent": self.emails_sent,
                "emails_opened": self.emails_opened,
                "links_clicked": self.links_clicked,
                "data_submitted": self.data_submitted,
                "data_collected": getattr(self, "data_collected", 0),
                "total_screenshots": self.total_screenshots
            })

        data["plugin_ids"] = self.plugin_ids or []
        data["module_ids"] = self.module_ids or []
        data["selkies_config"] = self.selkies_config or {}
        data["advanced_options"] = self.advanced_options or {}

        if include_victims:
            data["victims"] = [v.to_dict() for v in self.victims if v.is_active]

        return data

    def update_stats(self, db_session):
        """Update campaign statistics"""
        from models.victim import Victim
        from models.victim_event import EventType, VictimEvent

        # Count active victims.
        self.victims_count = db_session.query(Victim).filter(
            Victim.campaign_id == self.id,
            Victim.is_active == True
        ).count()

        # Derive email statistics from victim timestamps.
        email_stats = db_session.query(
            func.count(Victim.id).label('total'),
            func.sum(func.cast(Victim.email_opened_at.isnot(None), Integer)).label('opened'),
            func.sum(func.cast(Victim.email_link_clicked_at.isnot(None), Integer)).label('clicked'),
            func.sum(func.cast(Victim.data_submitted_at.isnot(None), Integer)).label('submitted')
        ).filter(
            Victim.campaign_id == self.id
        ).first()

        if email_stats:
            self.emails_opened = email_stats.opened or 0
            self.links_clicked = email_stats.clicked or 0
            self.data_submitted = email_stats.submitted or 0

        collection_events = (
            EventType.FORM_SUBMISSION,
            EventType.COOKIE_CAPTURED,
            EventType.FILE_DOWNLOADED,
            EventType.FILE_UPLOADED,
            EventType.SCREENSHOT,
            EventType.KEYLOG,
        )
        self.data_collected = db_session.query(func.count(Victim.id)).filter(
            Victim.campaign_id == self.id,
            or_(
                Victim.data_submitted_at.isnot(None),
                Victim.data_collections.any(),
                Victim.events.any(
                    VictimEvent.event_type.in_(collection_events)
                ),
            ),
        ).scalar() or 0

        self.updated_at = utc_now()
        db_session.commit()

    def __repr__(self):
        return f"<Campaign {self.name} ({self.status.value})>"
