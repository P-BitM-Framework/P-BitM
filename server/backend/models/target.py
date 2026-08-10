# admin-backend/models/target.py

from sqlalchemy import Column, ForeignKey, Index, JSON, String
from sqlalchemy.orm import relationship

from database import Base
from models.types import UTCDateTime, utc_now

class Target(Base):
    """
    Individual contact in the database.
    Reusable across multiple campaigns via TargetLists.
    """
    __tablename__ = "targets"

    # Primary Key
    id = Column(String, primary_key=True)

    # Foreign Key
    target_list_id = Column(
        String,
        ForeignKey("target_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Contact Information
    email = Column(String, nullable=False, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    position = Column(String, nullable=True)
    department = Column(String, nullable=True)

    # Custom fields
    # Example: {"phone": "+1234567890", "location": "Milan", "manager": "John Doe"}
    custom_fields = Column(JSON, default=dict, nullable=False)

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

    # Relationships
    target_list = relationship("TargetList", back_populates="targets")

    # Indexes for performance
    __table_args__ = (
        Index('idx_target_email', 'email'),
        Index('idx_target_list_id', 'target_list_id'),
    )

    def to_dict(self):
        data = {
            "id": self.id,
            "target_list_id": self.target_list_id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "position": self.position,
            "department": self.department,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        data["custom_fields"] = self.custom_fields or {}

        return data

    def __repr__(self):
        return f"<Target {self.email} in list {self.target_list_id}>"
