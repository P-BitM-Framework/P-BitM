# admin-backend/routes/target_lists.py

import logging
from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File, Query
from models.user import User
from routes.auth import get_current_user_from_session, require_operator
from utils.target_list import generate_csv_response
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from utils.request_models import ensure_json_size
from database import get_db
from models import TargetList, Target
import uuid
import csv
import io

router = APIRouter()
logger = logging.getLogger(__name__)

# ========== Pydantic Schemas ==========

class TargetListCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    company: str | None = Field(default=None, max_length=200)

class TargetListUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    company: str | None = Field(default=None, max_length=200)

class TargetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    email: EmailStr
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    position: str | None = Field(default=None, max_length=200)
    department: str | None = Field(default=None, max_length=200)
    custom_fields: dict = Field(default_factory=dict)

    @field_validator("custom_fields")
    @classmethod
    def validate_custom_fields(cls, value: dict) -> dict:
        return ensure_json_size(value, 64 * 1024, "custom_fields")

class TargetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    email: EmailStr = None
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    position: str | None = Field(default=None, max_length=200)
    department: str | None = Field(default=None, max_length=200)
    custom_fields: dict = None

    @field_validator("custom_fields")
    @classmethod
    def validate_custom_fields(cls, value: dict | None) -> dict | None:
        if value is not None:
            ensure_json_size(value, 64 * 1024, "custom_fields")
        return value

class TargetListResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    company: Optional[str] = None
    total_targets: int
    usage_count: int
    created_at: str
    updated_at: Optional[str] = None
    last_used_at: Optional[str] = None

class TargetListsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_lists: List[TargetListResponse]
    total: int = 0

# ========== Target List Endpoints ==========

@router.get("", response_model=TargetListsResponse)
async def list_target_lists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    """Get all target lists."""
    lists = db.query(TargetList).all()

    result = [tl.to_dict() for tl in lists]
    return {
        "target_lists": result,
        "total": len(result)
    }

@router.get("/{list_id}")
async def get_target_list(
    list_id: str,
    include_targets: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    """Get target list by ID (optionally with all targets)."""

    target_list = db.query(TargetList).filter_by(id=list_id).first()

    if not target_list:
        raise HTTPException(status_code=404, detail="Target list not found")

    return target_list.to_dict(include_targets=include_targets)


@router.post("", status_code=201)
async def create_target_list(
    data: TargetListCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Create new target list."""

    # Check if name exists
    existing = db.query(TargetList).filter_by(name=data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Target list with this name already exists")

    # Create list
    target_list = TargetList(
        id=str(uuid.uuid4())[:8],
        name=data.name,
        description=data.description,
        company=data.company
    )

    db.add(target_list)
    db.commit()
    db.refresh(target_list)

    logger.info(
        "Target list created: %s (by %s)", target_list.name, current_user.username
    )

    return target_list.to_dict()


@router.put("/{list_id}")
async def update_target_list(
    list_id: str,
    data: TargetListUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Update target list."""

    target_list = db.query(TargetList).filter_by(id=list_id).first()
    if not target_list:
        raise HTTPException(status_code=404, detail="Target list not found")

    # Update fields
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(target_list, key, value)

    db.commit()
    db.refresh(target_list)

    logger.info(
        "Target list updated: %s (by %s)", target_list.name, current_user.username
    )

    return target_list.to_dict()


@router.delete("/{list_id}")
async def delete_target_list(
    list_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Delete target list and all its targets."""

    target_list = db.query(TargetList).filter_by(id=list_id).first()
    if not target_list:
        raise HTTPException(status_code=404, detail="Target list not found")

    # Check if used in campaigns
    if target_list.campaigns:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: list is used in {len(target_list.campaigns)} campaign(s)"
        )

    target_count = target_list.total_targets
    db.delete(target_list)  # Cascade deletes all targets
    db.commit()

    logger.info(
        "Target list deleted: %s with %s target(s) (by %s)",
        target_list.name,
        target_count,
        current_user.username,
    )

    return {"message": "Target list deleted successfully"}


# ========== Target Management (nested in list) ==========

@router.get("/{list_id}/targets")
async def list_targets_in_list(
    list_id: str,
    skip: int = Query(0, ge=0, le=1_000_000),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    """Get all targets in a specific list."""

    target_list = db.query(TargetList).filter_by(id=list_id).first()
    if not target_list:
        raise HTTPException(status_code=404, detail="Target list not found")

    targets = db.query(Target).filter_by(
        target_list_id=list_id
    ).offset(skip).limit(limit).all()

    return {
        "list_id": list_id,
        "list_name": target_list.name,
        "total_targets": target_list.total_targets,
        "targets": [t.to_dict() for t in targets]
    }


@router.post("/{list_id}/targets", status_code=201)
async def add_target_to_list(
    list_id: str,
    data: TargetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Add new target to list."""

    # Verify list exists
    target_list = db.query(TargetList).filter_by(id=list_id).first()
    if not target_list:
        raise HTTPException(status_code=404, detail="Target list not found")

    # Check if email already exists in this list
    existing = db.query(Target).filter_by(
        target_list_id=list_id,
        email=data.email
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Target with email {data.email} already exists in this list"
        )

    # Create target
    target = Target(
        id=str(uuid.uuid4()),
        target_list_id=list_id,
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        position=data.position,
        department=data.department,
        custom_fields=data.custom_fields or {},
    )

    db.add(target)
    db.commit()

    # Update list stats
    target_list.update_stats(db)

    logger.info(
        "Target added to list %s: %s (by %s)",
        target_list.name,
        target.email,
        current_user.username,
    )

    return target.to_dict()


@router.get("/{list_id}/targets/{target_id}")
async def get_target_in_list(
    list_id: str,
    target_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    """Get specific target in list."""

    target = db.query(Target).filter_by(
        id=target_id,
        target_list_id=list_id
    ).first()

    if not target:
        raise HTTPException(status_code=404, detail="Target not found in this list")

    return target.to_dict()


@router.put("/{list_id}/targets/{target_id}")
async def update_target_in_list(
    list_id: str,
    target_id: str,
    data: TargetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Update target in list."""

    target = db.query(Target).filter_by(
        id=target_id,
        target_list_id=list_id
    ).first()

    if not target:
        raise HTTPException(status_code=404, detail="Target not found in this list")

    # Update fields
    update_data = data.dict(exclude_unset=True)

    # Handle custom_fields
    if 'custom_fields' in update_data and update_data['custom_fields'] is not None:
        update_data["custom_fields"] = update_data["custom_fields"] or {}

    for key, value in update_data.items():
        setattr(target, key, value)

    db.commit()
    db.refresh(target)

    logger.info(
        "Target updated in list %s: %s (by %s)",
        list_id,
        target.email,
        current_user.username,
    )

    return target.to_dict()


@router.delete("/{list_id}/targets/{target_id}")
async def delete_target_from_list(
    list_id: str,
    target_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """Delete target from list."""

    target = db.query(Target).filter_by(
        id=target_id,
        target_list_id=list_id
    ).first()

    if not target:
        raise HTTPException(status_code=404, detail="Target not found in this list")

    target_list = target.target_list
    target_email = target.email

    db.delete(target)
    db.commit()

    # Update list stats
    target_list.update_stats(db)

    logger.info(
        "Target deleted from list %s: %s (by %s)",
        target_list.name,
        target_email,
        current_user.username,
    )

    return {"message": "Target deleted successfully"}


@router.get("/{list_id}/export-csv")
async def export_targets_csv(
    list_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    """Export all targets to CSV."""
    from fastapi.responses import StreamingResponse
    from datetime import datetime
    import re

    target_list = db.query(TargetList).filter_by(id=list_id).first()
    if not target_list:
        raise HTTPException(status_code=404, detail="Target list not found")

    # Materialize the query before writing the CSV response.
    targets = list(target_list.targets)

    return generate_csv_response(
        targets=targets,
        list_name=target_list.name,
        export_type="all"
    )


@router.post("/{list_id}/targets/bulk")
async def bulk_add_targets(
    list_id: str,
    targets: List[TargetCreate] = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """
    Add multiple targets at once via JSON.

    Example payload:
    [
        {
            "email": "john@company.com",
            "first_name": "John",
            "last_name": "Doe",
            "position": "Manager"
        },
        {
            "email": "jane@company.com",
            "first_name": "Jane",
            "last_name": "Smith"
        }
    ]
    """

    # Verify list exists
    target_list = db.query(TargetList).filter_by(id=list_id).first()
    if not target_list:
        raise HTTPException(status_code=404, detail="Target list not found")

    created = 0
    skipped = 0
    errors = []

    for idx, data in enumerate(targets, start=1):
        # Check if exists
        existing = db.query(Target).filter_by(
            target_list_id=list_id,
            email=data.email
        ).first()

        if existing:
            skipped += 1
            errors.append(f"Entry {idx}: Email '{data.email}' already exists")
            continue

        # Create target
        target = Target(
            id=str(uuid.uuid4()),
            target_list_id=list_id,
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
            position=data.position,
            department=data.department,
            custom_fields=data.custom_fields or {},
        )

        db.add(target)
        created += 1

    db.commit()

    # Update list stats
    target_list.update_stats(db)

    logger.info(
        "Bulk target add to list %s: %s created, %s skipped (by %s)",
        target_list.name,
        created,
        skipped,
        current_user.username,
    )

    return {
        "message": "Bulk create completed",
        "list_id": list_id,
        "list_name": target_list.name,
        "created": created,
        "skipped": skipped,
        "total_targets": target_list.total_targets,
        "errors": errors[:20]
    }

@router.post("/{list_id}/targets/bulk-delete")
async def bulk_delete_targets(
    list_id: str,
    target_ids: List[str] = Body(embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """
    Delete multiple targets at once via JSON.

    Example payload:
    {
        "target_ids": ["target-id-1", "target-id-2", "target-id-3"]
    }
    """

    # Verify list exists
    target_list = db.query(TargetList).filter_by(id=list_id).first()
    if not target_list:
        raise HTTPException(status_code=404, detail="Target list not found")

    deleted = 0
    errors = []

    for target_id in target_ids:
        target = db.query(Target).filter_by(
            id=target_id,
            target_list_id=list_id
        ).first()

        if not target:
            errors.append(f"Target ID '{target_id}' not found in this list")
            continue

        db.delete(target)
        deleted += 1

    db.commit()

    # Update list stats
    target_list.update_stats(db)

    logger.info(
        "Bulk target delete from list %s: %s deleted (by %s)",
        target_list.name,
        deleted,
        current_user.username,
    )

    return {
        "message": "Bulk delete completed",
        "list_id": list_id,
        "list_name": target_list.name,
        "deleted": deleted,
        "total_targets": target_list.total_targets,
        "errors": errors[:20]
    }


@router.delete("/{list_id}/targets")
async def clear_all_targets(
    list_id: str,
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    """
    Delete ALL targets from list (dangerous!).
    Requires confirm=true query parameter.
    """

    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to delete all targets"
        )

    target_list = db.query(TargetList).filter_by(id=list_id).first()
    if not target_list:
        raise HTTPException(status_code=404, detail="Target list not found")

    # Delete all targets
    count = db.query(Target).filter_by(target_list_id=list_id).delete()

    db.commit()

    # Update stats
    target_list.update_stats(db)

    logger.info(
        "All targets cleared from list %s: %s deleted (by %s)",
        target_list.name,
        count,
        current_user.username,
    )

    return {
        "message": f"Deleted {count} targets from list '{target_list.name}'",
        "deleted_count": count
    }
