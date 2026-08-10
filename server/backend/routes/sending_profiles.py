# admin-backend/routes/sending_profiles.py

from fastapi import APIRouter, Depends, HTTPException, Query
from models.user import User
from routes.auth import get_current_user_from_session, require_operator
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from database import get_db
from models import SMTPProfile
from utils.email_sender import EmailSender
from utils.secret_storage import decrypt_secret, encrypt_secret
from utils.permissions import can_manage_resources
import logging
import uuid

router = APIRouter()
logger = logging.getLogger(__name__)

# ========== Pydantic Schemas ==========

class SMTPProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    smtp_host: str = Field(min_length=1, max_length=253)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = Field(max_length=512)
    smtp_password: str = Field(max_length=4096)
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    ignore_cert_errors: bool = False
    from_email: EmailStr
    from_name: str | None = Field(default=None, max_length=256)
    domain: str | None = Field(default=None, max_length=253)
    tracking_domain: str | None = Field(default=None, max_length=253)
    dkim_enabled: bool = False
    dkim_selector: str | None = Field(default=None, max_length=128)
    dkim_private_key: str | None = Field(default=None, max_length=64 * 1024)

    @model_validator(mode="after")
    def validate_transport(self):
        if self.smtp_use_tls and self.smtp_use_ssl:
            raise ValueError("SMTP TLS and implicit SSL cannot both be enabled")
        if self.ignore_cert_errors and not (
            self.smtp_use_tls or self.smtp_use_ssl
        ):
            raise ValueError(
                "Certificate verification can only be disabled for SSL or TLS"
            )
        return self

class SMTPProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    smtp_host: str | None = Field(default=None, min_length=1, max_length=253)
    smtp_port: int | None = Field(default=None, ge=1, le=65535)
    smtp_username: str | None = Field(default=None, max_length=512)
    smtp_password: str | None = Field(default=None, max_length=4096)
    smtp_use_tls: bool | None = None
    smtp_use_ssl: bool | None = None
    ignore_cert_errors: bool | None = None
    from_email: EmailStr = None
    from_name: str | None = Field(default=None, max_length=256)
    domain: str | None = Field(default=None, max_length=253)
    tracking_domain: str | None = Field(default=None, max_length=253)
    dkim_enabled: bool | None = None
    dkim_selector: str | None = Field(default=None, max_length=128)
    dkim_private_key: str | None = Field(default=None, max_length=64 * 1024)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_transport(self):
        if self.smtp_use_tls is True and self.smtp_use_ssl is True:
            raise ValueError("SMTP TLS and implicit SSL cannot both be enabled")
        return self

class SMTPProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_use_tls: bool
    smtp_use_ssl: bool
    ignore_cert_errors: bool
    from_email: EmailStr
    from_name: str | None = None
    domain: str | None = None
    tracking_domain: str | None = None
    is_active: bool
    usage_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None
    last_used_at: str | None = None
    campaigns_count: int | None = 0

class SMTPProfilesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profiles: List[SMTPProfileResponse]
    total: int = 0

# ========== Endpoints ==========

@router.get("", response_model=SMTPProfilesResponse)
async def list_sending_profiles(
    skip: int = Query(0, ge=0, le=1_000_000),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    """Get all sending profiles."""
    profiles = db.query(SMTPProfile).offset(skip).limit(limit).all()

    profiles = [p.to_dict() for p in profiles]

    return {
        "profiles": profiles,
        "total": len(profiles)
    }


@router.get("/{profile_id}")
async def get_sending_profile(
    profile_id: str,
    include_password: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    """Get sending profile by ID."""
    profile = db.query(SMTPProfile).filter_by(id=profile_id).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Sending profile not found")

    if include_password and not can_manage_resources(current_user):
        raise HTTPException(status_code=403, detail="Operator privileges required")

    result = profile.to_dict()
    if include_password:
        result["smtp_password"] = decrypt_secret(profile.smtp_password)
        result["dkim_private_key"] = decrypt_secret(profile.dkim_private_key)
    return result


@router.post("", status_code=201)
async def create_sending_profile(
    data: SMTPProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Create new sending profile."""

    # Check if name already exists
    existing = db.query(SMTPProfile).filter_by(name=data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Sending profile with this name already exists")

    # Create profile
    profile = SMTPProfile(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        smtp_host=data.smtp_host,
        smtp_port=data.smtp_port,
        smtp_username=data.smtp_username,
        smtp_password=encrypt_secret(data.smtp_password),
        smtp_use_tls=data.smtp_use_tls,
        smtp_use_ssl=data.smtp_use_ssl,
        ignore_cert_errors=data.ignore_cert_errors,
        from_email=data.from_email,
        from_name=data.from_name,
        domain=data.domain,
        tracking_domain=data.tracking_domain,
        dkim_enabled=data.dkim_enabled,
        dkim_selector=data.dkim_selector,
        dkim_private_key=encrypt_secret(data.dkim_private_key)
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    logger.info(
        "Sending profile created: %s (%s:%s, by %s)",
        profile.name,
        profile.smtp_host,
        profile.smtp_port,
        current_user.username,
    )

    return profile.to_dict()


@router.put("/{profile_id}")
async def update_sending_profile(
    profile_id: str,
    data: SMTPProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Update sending profile."""

    profile = db.query(SMTPProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Sending profile not found")

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    resulting_tls = update_data.get("smtp_use_tls", profile.smtp_use_tls)
    resulting_ssl = update_data.get("smtp_use_ssl", profile.smtp_use_ssl)
    resulting_ignore_cert_errors = update_data.get(
        "ignore_cert_errors",
        profile.ignore_cert_errors,
    )
    if resulting_tls and resulting_ssl:
        raise HTTPException(
            status_code=400,
            detail="SMTP TLS and implicit SSL cannot both be enabled",
        )
    if resulting_ignore_cert_errors and not (
        resulting_tls or resulting_ssl
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Certificate verification can only be disabled for SSL or TLS"
            ),
        )
    for field_name in ("smtp_password", "dkim_private_key"):
        if field_name in update_data:
            update_data[field_name] = encrypt_secret(update_data[field_name])
    for key, value in update_data.items():
        setattr(profile, key, value)

    success, message = EmailSender(profile).test_connection()
    if not success:
        attempted_name = profile.name
        attempted_host = profile.smtp_host
        attempted_port = profile.smtp_port
        db.rollback()
        logger.warning(
            "Sending profile update rejected after SMTP test failed: "
            "%s (%s:%s, by %s): %s",
            attempted_name,
            attempted_host,
            attempted_port,
            current_user.username,
            message,
        )
        raise HTTPException(
            status_code=400,
            detail=f"SMTP settings were not saved: {message}",
        )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(profile)

    logger.info(
        "Sending profile updated and SMTP connection verified: %s (by %s)",
        profile.name,
        current_user.username,
    )

    return profile.to_dict()


@router.delete("/{profile_id}")
async def delete_sending_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Delete sending profile."""

    profile = db.query(SMTPProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Sending profile not found")

    # Check if used in campaigns
    if profile.campaigns:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: profile is used in {len(profile.campaigns)} campaign(s)"
        )

    db.delete(profile)
    db.commit()

    logger.info(
        "Sending profile deleted: %s (by %s)", profile.name, current_user.username
    )

    return {"message": "Sending profile deleted successfully"}


@router.post("/{profile_id}/test")
async def test_sending_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Test SMTP connection for sending profile."""

    profile = db.query(SMTPProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Sending profile not found")

    # Test connection
    sender = EmailSender(profile)
    success, message = sender.test_connection()

    if success:
        logger.info(
            "SMTP test succeeded for profile %s (by %s)",
            profile.name,
            current_user.username,
        )
    else:
        logger.warning(
            "SMTP test failed for profile %s (by %s): %s",
            profile.name,
            current_user.username,
            message,
        )

    return {
        "success": success,
        "message": message,
        "profile_id": profile_id,
        "smtp_host": profile.smtp_host,
        "smtp_port": profile.smtp_port
    }
