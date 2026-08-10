# models.py

from database import Base
from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship
import uuid

from models.types import UTCDateTime, utc_now


class LandingPage(Base):
    __tablename__ = "landing_pages"

    id = Column(String, default=lambda: str(uuid.uuid4())[:8], primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    content = Column(Text)
    created_at = Column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    campaigns = relationship("Campaign", back_populates="landing_page")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
