# admin-backend/models/sending_profile.py

from sqlalchemy import Boolean, Column, Integer, String, Text, text
from sqlalchemy.orm import relationship

from database import Base
from models.types import UTCDateTime, utc_now

class SMTPProfile(Base):
    """
    SMTP configuration for sending phishing emails.
    Reusable across multiple campaigns.
    """
    __tablename__ = "sending_profiles"

    # Primary Key
    id = Column(String, primary_key=True)

    # Basic Info
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # SMTP Settings
    smtp_host = Column(String, nullable=False)
    smtp_port = Column(Integer, nullable=False, default=587)
    smtp_username = Column(String, nullable=False)
    smtp_password = Column(String, nullable=False)
    smtp_use_tls = Column(Boolean, default=True, nullable=False)
    smtp_use_ssl = Column(Boolean, default=False, nullable=False)
    ignore_cert_errors = Column(
        Boolean,
        default=False,
        server_default=text("0"),
        nullable=False,
    )

    # Email Headers
    from_email = Column(String, nullable=False)  # Envelope MAIL FROM (e.g., "bot@company.com")
    from_name = Column(String, nullable=True)      # Display name (e.g., "IT Security Team")

    # Advanced Settings (optional)
    domain = Column(String, nullable=True)              # e.g., "company.com"
    tracking_domain = Column(String, nullable=True)     # e.g., "track.company.com"

    # DKIM Settings (optional)
    dkim_enabled = Column(Boolean, default=False, nullable=False)
    dkim_selector = Column(String, nullable=True)       # e.g., "default"
    dkim_private_key = Column(Text, nullable=True)      # Encrypted PEM payload

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    created_at = Column(
        UTCDateTime(),
        default=utc_now,
        nullable=False
    )
    updated_at = Column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    last_used_at = Column(UTCDateTime(), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)

    # Relationships
    campaigns = relationship("Campaign", back_populates="sending_profile")

    def to_dict(self, include_password=False):
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "smtp_username": self.smtp_username,
            "smtp_use_tls": self.smtp_use_tls,
            "smtp_use_ssl": self.smtp_use_ssl,
            "ignore_cert_errors": self.ignore_cert_errors,
            "from_email": self.from_email,
            "from_name": self.from_name,
            "domain": self.domain,
            "tracking_domain": self.tracking_domain,
            "dkim_enabled": self.dkim_enabled,
            "dkim_selector": self.dkim_selector,
            "is_active": self.is_active,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "campaigns_count": len(self.campaigns) if self.campaigns else 0
        }

        return data

    def __repr__(self):
        return f"<SMTPProfile {self.name} ({self.smtp_host}:{self.smtp_port})>"
