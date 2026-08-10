# admin-backend/models/target_list.py

from models.target import Target
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base
from models.types import UTCDateTime, utc_now

class TargetList(Base):
    """
    Collection of targets (contacts).
    Reusable across multiple campaigns.
    """
    __tablename__ = "target_lists"

    # Primary Key
    id = Column(String, primary_key=True)

    # Basic Info
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    company = Column(String, nullable=True)

    # Stats (computed/cached)
    total_targets = Column(Integer, default=0, nullable=False)

    # Metadata
    created_at = Column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
        index=True
    )
    updated_at = Column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    last_used_at = Column(UTCDateTime(), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)  # Count of campaigns using this list

    # Relationships
    targets = relationship(
        "Target",
        back_populates="target_list",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    campaigns = relationship("Campaign", back_populates="target_list")

    def to_dict(self, include_targets=False):
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "company": self.company,
            "total_targets": self.total_targets,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

        if include_targets:
            data["targets"] = [t.to_dict() for t in self.targets]

        return data

    def update_stats(self, db_session):
        """Update total_targets count"""

        count = db_session.query(Target).filter_by(target_list_id=self.id).count()

        self.total_targets = count
        self.updated_at = utc_now()
        db_session.commit()




    def __repr__(self):
        return f"<TargetList {self.name} ({self.total_targets} targets)>"
