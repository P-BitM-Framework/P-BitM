# models/module.py

from database import Base
from sqlalchemy import Column, JSON, String, Text
import uuid

from models.types import UTCDateTime, utc_now


class Module(Base):
    __tablename__ = "modules"

    id = Column(String, default=lambda: str(uuid.uuid4())[:8], primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String, nullable=False)
    icon = Column(Text)  # Base64 encoded image 160x160
    inputs = Column(JSON, default=list, nullable=False)
    payload = Column(Text, nullable=False)  # JavaScript payload
    link = Column(String, default="/data")  # Optional link/reference
    created_at = Column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "icon": self.icon,
            "inputs": self.inputs if self.inputs else [],
            "payload": self.payload,
            "link": self.link,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
