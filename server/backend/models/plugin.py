import logging
import uuid
from typing import List

from sqlalchemy import Column, JSON, String, Text
from database import Base
from pydantic import BaseModel, ConfigDict, Field

from models.types import UTCDateTime, utc_now


logger = logging.getLogger(__name__)

class PluginFile(BaseModel):
    """Represents a single file within a plugin"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "manifest.json",
                "content": '{"manifest_version": 2, "name": "My Plugin"}',
            }
        }
    )

    name: str = Field(..., description="File name (e.g., 'manifest.json', 'background.js')")
    content: str = Field(..., description="File content as string")

class Plugin(Base):
    __tablename__ = 'plugins'

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4())[:8])
    name = Column(String, nullable=False)
    description = Column(Text)
    files = Column(JSON, default=list, nullable=False)
    created_at = Column(UTCDateTime(), default=utc_now, nullable=False)
    updated_at = Column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    def get_files(self) -> List[PluginFile]:
        """Validate persisted plugin files and return typed values."""
        if not self.files:
            return []

        try:
            return [PluginFile(**file_dict) for file_dict in self.files]
        except (TypeError, ValueError) as exc:
            logger.warning("Invalid persisted plugin file metadata: %s", exc)
            return []

    def set_files(self, files: List[PluginFile]):
        """Persist a validated list of plugin files."""
        self.files = [file.model_dump() for file in files]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "files": self.files or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
