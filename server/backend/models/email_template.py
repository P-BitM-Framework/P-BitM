# admin-backend/models/email_template.py

from sqlalchemy import Boolean, Column, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from database import Base
from models.types import UTCDateTime, utc_now

class EmailTemplate(Base):
    """
    Reusable email template (lure) for phishing campaigns.
    Contains subject, HTML body, and text fallback.
    """
    __tablename__ = "email_templates"

    # Primary Key
    id = Column(String, primary_key=True)

    # Basic Info
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Email Content
    subject = Column(String, nullable=False)
    html_content = Column(Text, nullable=False)
    text_content = Column(Text, nullable=True)  # Plain text fallback

    # Template Variables (JSON array)
    # Example: ["{{first_name}}", "{{company}}", "{{tracking_url}}"]
    # These will be replaced when sending emails
    variables = Column(JSON, default=list, nullable=False)

    # Category/Tags
    category = Column(String, nullable=True, index=True)  # e.g., "credential_harvest", "attachment", "link"
    tags = Column(JSON, default=list, nullable=False)

    # Attachments (optional, JSON array of file info)
    # Example: [{"filename": "invoice.pdf", "path": "/storage/attachments/xyz.pdf"}]
    attachments = Column(JSON, default=list, nullable=False)

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
    campaigns = relationship("Campaign", back_populates="email_template")

    def to_dict(self):
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "subject": self.subject,
            "html_content": self.html_content,
            "text_content": self.text_content,
            "category": self.category,
            "is_active": self.is_active,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

        data["variables"] = self.variables or []
        data["tags"] = self.tags or []
        data["attachments"] = self.attachments or []

        return data

    def extract_variables(self):
        """
        Extract template variables from subject and html_content.
        Returns list of unique variables like ["{{first_name}}", "{{tracking_url}}"]
        """
        import re
        pattern = r'\{\{[\w_]+\}\}'

        variables = set()

        # Extract from subject
        if self.subject:
            variables.update(re.findall(pattern, self.subject))

        # Extract from HTML content
        if self.html_content:
            variables.update(re.findall(pattern, self.html_content))

        # Extract from text content
        if self.text_content:
            variables.update(re.findall(pattern, self.text_content))

        return sorted(list(variables))

    def __repr__(self):
        return f"<EmailTemplate {self.name} (used {self.usage_count}x)>"
