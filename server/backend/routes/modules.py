# routes/modules.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database import get_db
from models import Module, User
from routes.auth import get_current_user_from_session, require_operator
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# Schemas
class ModuleInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: int = Field(ge=0, le=10_000)
    label: str = Field(min_length=1, max_length=120)
    type: str = Field(min_length=1, max_length=32)
    required: bool


class ModuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=4000)
    category: str = Field(min_length=1, max_length=80)
    icon: Optional[str] = Field(default=None, max_length=1024 * 1024)
    inputs: List[ModuleInput] = Field(default_factory=list, max_length=64)
    payload: str = Field(min_length=1, max_length=1024 * 1024)
    link: Optional[str] = Field(default=None, max_length=2048)


class ModuleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=4000)
    category: Optional[str] = Field(default=None, min_length=1, max_length=80)
    icon: Optional[str] = Field(default=None, max_length=1024 * 1024)
    inputs: Optional[List[ModuleInput]] = Field(default=None, max_length=64)
    payload: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=1024 * 1024,
    )
    link: Optional[str] = Field(default=None, max_length=2048)


# Get all modules
@router.get("")
async def get_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    modules = db.query(Module).all()
    return {
        "modules": [module.to_dict() for module in modules]
    }


# Get single module
@router.get("/{module_id}")
async def get_module(
    module_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    return module.to_dict()


# Create module
@router.post("")
async def create_module(
    data: ModuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    module = Module(
        name=data.name,
        description=data.description,
        category=data.category,
        icon=data.icon,
        inputs=[input_item.dict() for input_item in data.inputs],
        payload=data.payload,
        link=data.link,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db.add(module)
    db.commit()
    db.refresh(module)

    logger.info("Module created: %s (by %s)", module.name, current_user.username)

    return module.to_dict()


# Update module
@router.put("/{module_id}")
async def update_module(
    module_id: str,
    data: ModuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    if data.name is not None:
        module.name = data.name
    if data.description is not None:
        module.description = data.description
    if data.category is not None:
        module.category = data.category
    if data.icon is not None:
        module.icon = data.icon
    if data.inputs is not None:
        module.inputs = [input_item.dict() for input_item in data.inputs]
    if data.payload is not None:
        module.payload = data.payload
    if data.link is not None:
        module.link = data.link

    module.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(module)

    logger.info("Module updated: %s (by %s)", module.name, current_user.username)

    return module.to_dict()


# Delete module
@router.delete("/{module_id}")
async def delete_module(
    module_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    db.delete(module)
    db.commit()

    logger.info("Module deleted: %s (by %s)", module.name, current_user.username)

    return {"message": "Module deleted successfully"}


# Export module
@router.get("/{module_id}/export")
async def export_module(
    module_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    from fastapi.responses import Response
    import json

    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Sanitize filename
    safe_name = "".join(c for c in module.name if c.isalnum() or c in (' ', '-', '_')).strip()

    # Export as JSON
    export_data = module.to_dict()

    return Response(
        content=json.dumps(export_data, indent=2),
        media_type='application/json',
        headers={
            "Content-Disposition": f"attachment; filename={safe_name}.json"
        }
    )


# Clone module
@router.post("/{module_id}/clone")
async def clone_module(
    module_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    original = db.query(Module).filter(Module.id == module_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Module not found")

    cloned = Module(
        name=f"{original.name} (Copy)",
        description=original.description,
        category=original.category,
        icon=original.icon,
        inputs=original.inputs,
        payload=original.payload,
        link=original.link,
        created_at=datetime.now(timezone.utc)
    )

    db.add(cloned)
    db.commit()
    db.refresh(cloned)

    logger.info(
        "Module cloned: %s -> %s (by %s)",
        original.name,
        cloned.name,
        current_user.username,
    )

    return cloned.to_dict()
