# admin-backend/routes/email_templates.py
from fastapi import APIRouter, Depends, HTTPException, Query
from models.user import User
from routes.auth import get_current_user_from_session, require_operator
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from utils.request_models import ensure_json_size
from database import get_db
from models import EmailTemplate
import logging
import uuid
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

# ========== Pydantic Schemas ==========

class EmailTemplateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    subject: str = Field(min_length=1, max_length=998)
    html_content: str = Field(min_length=1, max_length=5 * 1024 * 1024)
    text_content: str | None = Field(default=None, max_length=5 * 1024 * 1024)
    category: str | None = Field(default=None, max_length=80)
    tags: List[str] = Field(default_factory=list, max_length=64)
    attachments: List[dict] = Field(default_factory=list, max_length=32)
    variables: List[str] = Field(default_factory=list, max_length=128)

    @field_validator("attachments")
    @classmethod
    def validate_attachments(cls, value: List[dict]) -> List[dict]:
        return ensure_json_size(value, 256 * 1024, "attachments")


class EmailTemplateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    subject: str | None = Field(default=None, min_length=1, max_length=998)
    html_content: str | None = Field(
        default=None,
        min_length=1,
        max_length=5 * 1024 * 1024,
    )
    text_content: str | None = Field(default=None, max_length=5 * 1024 * 1024)
    category: str | None = Field(default=None, max_length=80)
    tags: List[str] | None = Field(default=None, max_length=64)
    attachments: List[dict] | None = Field(default=None, max_length=32)
    variables: List[str] | None = Field(default=None, max_length=128)
    is_active: bool | None = None

    @field_validator("attachments")
    @classmethod
    def validate_attachments(
        cls,
        value: List[dict] | None,
    ) -> List[dict] | None:
        if value is not None:
            ensure_json_size(value, 256 * 1024, "attachments")
        return value

class EmailTemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    subject: str
    html_content: Optional[str] = None
    text_content: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    attachments: List[dict] = Field(default_factory=list)
    variables: List[str] = Field(default_factory=list)
    is_active: bool = True
    usage_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None


class EmailTemplatesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    templates: List[EmailTemplateResponse]
    total: int = 0

# ========== Endpoints ==========

@router.get("", response_model=EmailTemplatesResponse)
async def list_email_templates(
    skip: int = Query(0, ge=0, le=1_000_000),
    limit: int = Query(100, ge=1, le=500),
    category: str = None,
    is_active: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    """Get all email templates."""

    query = db.query(EmailTemplate)

    if category:
        query = query.filter_by(category=category)

    if is_active is not None:
        query = query.filter_by(is_active=is_active)

    templates = query.offset(skip).limit(limit).all()

    result = [t.to_dict() for t in templates]

    return {
        "templates": result,
        "total": len(result)
    }


@router.get("/{template_id}")
async def get_email_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    """Get email template by ID."""

    template = db.query(EmailTemplate).filter_by(id=template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")

    return template.to_dict()


@router.post("", status_code=201)
async def create_email_template(
    data: EmailTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Create new email template."""

    # Check if name exists
    existing = db.query(EmailTemplate).filter_by(name=data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Template with this name already exists")

    # Create template
    template = EmailTemplate(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        subject=data.subject,
        html_content=data.html_content,
        text_content=data.text_content,
        category=data.category,
        tags=data.tags or [],
        attachments=data.attachments or [],
    )

    # Extract variables from template
    variables = template.extract_variables()
    template.variables = variables

    db.add(template)
    db.commit()
    db.refresh(template)

    logger.info(
        "Email template created: %s (by %s)", template.name, current_user.username
    )

    return template.to_dict()


@router.put("/{template_id}")
async def update_email_template(
    template_id: str,
    data: EmailTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Update email template."""

    template = db.query(EmailTemplate).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")

    # Update fields
    update_data = data.dict(exclude_unset=True)

    # Normalize optional list fields before assigning them to JSON columns.
    for field_name in ("tags", "attachments", "variables"):
        if field_name in update_data and update_data[field_name] is not None:
            update_data[field_name] = update_data[field_name] or []

    for key, value in update_data.items():
        setattr(template, key, value)

    # Re-extract variables if content changed
    if 'subject' in update_data or 'html_content' in update_data:
        variables = template.extract_variables()
        template.variables = variables

    db.commit()
    db.refresh(template)

    logger.info(
        "Email template updated: %s (by %s)", template.name, current_user.username
    )

    return template.to_dict()


@router.delete("/{template_id}")
async def delete_email_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Delete email template."""

    template = db.query(EmailTemplate).filter_by(id=template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")

    # Check if used in campaigns
    if template.campaigns:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: template is used in {len(template.campaigns)} campaign(s)"
        )

    db.delete(template)
    db.commit()

    logger.info(
        "Email template deleted: %s (by %s)", template.name, current_user.username
    )

    return {"message": "Email template deleted successfully"}


@router.post("/{template_id}/duplicate")
async def duplicate_email_template(
    template_id: str,
    new_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Duplicate existing email template."""

    original = db.query(EmailTemplate).filter_by(id=template_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Email template not found")

    # Create duplicate
    duplicate = EmailTemplate(
        id=str(uuid.uuid4()),
        name=new_name,
        description=f"Copy of {original.name}",
        subject=original.subject,
        html_content=original.html_content,
        text_content=original.text_content,
        category=original.category,
        tags=original.tags,
        variables=original.variables,
        attachments=original.attachments,
    )

    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)

    logger.info(
        "Email template duplicated: %s -> %s (by %s)",
        original.name,
        duplicate.name,
        current_user.username,
    )

    return duplicate.to_dict()
