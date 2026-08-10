# admin-backend/models/data_collection.py
import uuid
from sqlalchemy import Column, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import relationship

from database import Base
from models.types import UTCDateTime, utc_now

class DataCollection(Base):
    __tablename__ = 'data_collections'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4())[:8])

    # References
    victim_id = Column(String, ForeignKey('victims.id', ondelete='CASCADE'), nullable=False, index=True)
    campaign_id = Column(String, ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False, index=True)
    module_id = Column(String, ForeignKey('modules.id', ondelete='SET NULL'), nullable=True, index=True)

    # Data type
    data_type = Column(String, nullable=False, index=True)
    # Types: 'screenshot', 'keylog', 'file_hijacked',
    #        'cookie', 'password', 'credit_card', 'iban', 'module_data'

    # File info
    file_path = Column(String, nullable=True)
    file_size_bytes = Column(Integer)

    # Timing
    collected_at = Column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
        index=True,
    )

    # Metadata (JSON)
    extra_metadata = Column(JSON, nullable=True)

    # Relationships
    victim = relationship("Victim", back_populates="data_collections")
    campaign = relationship("Campaign", back_populates="data_collections")
    module = relationship("Module")

    __table_args__ = (
        Index('idx_data_campaign_type', 'campaign_id', 'data_type'),
        Index('idx_data_victim_type', 'victim_id', 'data_type'),
    )

    def to_dict(self):
        metadata = (
            self.extra_metadata
            if isinstance(self.extra_metadata, dict)
            else {}
        )

        data = {
            "id": self.id,
            "victim_id": self.victim_id,
            "campaign_id": self.campaign_id,
            "module_id": self.module_id,
            "data_type": self.data_type,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "file_size_mb": round(self.file_size_bytes / (1024 * 1024), 2) if self.file_size_bytes else 0,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None,
            "extra_metadata": metadata,
            "metadata": metadata,
        }
        return data
