# admin-backend/models/user.py
from sqlalchemy import Boolean, Column, String
from sqlalchemy.orm import relationship

from database import Base
from models.types import UTCDateTime, utc_now

class User(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False, default='operator')  # admin, operator
    created_at = Column(UTCDateTime(), default=utc_now, nullable=False)
    last_login = Column(UTCDateTime(), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    campaigns = relationship("Campaign", back_populates="creator", foreign_keys="Campaign.created_by")
    sessions = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

    def is_admin(self) -> bool:
        return self.role == "admin"
