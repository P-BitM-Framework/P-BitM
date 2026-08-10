from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import zipfile
import io
import logging
from fastapi.responses import StreamingResponse
from routes.auth import get_current_user_from_session, require_operator
from sqlalchemy.orm import Session
from database import get_db
from models.plugin import Plugin
from models.user import User
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
import json
from utils.plugin_files import (
    MAX_PLUGIN_ARCHIVE_BYTES,
    PluginFileValidationError,
    read_plugin_archive,
    validate_plugin_files,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# Pydantic schemas
class PluginFile(BaseModel):
    name: str
    content: str


class PluginCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default="", max_length=2000)


class PluginUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    files: Optional[List[dict]] = Field(default=None, max_length=128)


# Get all plugins
@router.get("")
async def get_plugins(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    plugins = db.query(Plugin).order_by(Plugin.created_at.desc()).all()
    return {"plugins": [p.to_dict() for p in plugins]}


# Get single plugin
@router.get("/{plugin_id}")
async def get_plugin(
    plugin_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    return plugin.to_dict()


# Create plugin
@router.post("")
async def create_plugin(
    data: PluginCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    plugin = Plugin(
        name=data.name,
        description=data.description,
        files=[],
    )

    db.add(plugin)
    db.commit()
    db.refresh(plugin)

    logger.info("Plugin created: %s (by %s)", plugin.name, current_user.username)

    return plugin.to_dict()


# Update plugin
@router.put("/{plugin_id}")
async def update_plugin(
    plugin_id: str,
    data: PluginUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    if data.name is not None:
        plugin.name = data.name
    if data.description is not None:
        plugin.description = data.description
    if data.files is not None:
        try:
            plugin.files = validate_plugin_files(data.files)
        except PluginFileValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    db.refresh(plugin)

    logger.info("Plugin updated: %s (by %s)", plugin.name, current_user.username)

    return plugin.to_dict()


# Delete plugin
@router.delete("/{plugin_id}")
async def delete_plugin(
    plugin_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    db.delete(plugin)
    db.commit()

    logger.info("Plugin deleted: %s (by %s)", plugin.name, current_user.username)

    return {"message": "Plugin deleted successfully"}


# Export plugin as JSON with optional victim_id replacement
@router.get("/{plugin_id}/export")
async def export_plugin(
    plugin_id: str,
    victim_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    # Parse files
    try:
        files_data = validate_plugin_files(plugin.files or [])
    except (json.JSONDecodeError, PluginFileValidationError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Plugin contains invalid file data",
        ) from exc

    # Create ZIP in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add plugin metadata
        metadata = {
            "name": plugin.name,
            "description": plugin.description,
            "created_at": plugin.created_at.isoformat() if plugin.created_at else None
        }
        zip_file.writestr("plugin.json", json.dumps(metadata, indent=2))

        # Add each file
        for file in files_data:
            filename = file.get("name", "untitled")
            content = file.get("content", "")

            # Replace VICTIM_ID placeholder if victim_id is provided
            if victim_id and "VICTIM_ID" in content:
                content = content.replace("VICTIM_ID", victim_id)

            zip_file.writestr(f"files/{filename}", content)

    zip_buffer.seek(0)

    # Sanitize filename
    safe_name = "".join(c for c in plugin.name if c.isalnum() or c in (' ', '-', '_')).strip()

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={safe_name}.zip"
        }
    )


@router.post("/import")
async def import_plugin(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    if not file.filename or not file.filename.lower().endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported")

    try:
        zip_content = await file.read(MAX_PLUGIN_ARCHIVE_BYTES + 1)
        if len(zip_content) > MAX_PLUGIN_ARCHIVE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Plugin archive exceeds the upload size limit",
            )
        zip_buffer = io.BytesIO(zip_content)

        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            metadata, files_data = read_plugin_archive(zip_file)

        plugin = Plugin(
            name=metadata["name"],
            description=metadata["description"],
            files=files_data,
        )

        db.add(plugin)
        db.commit()
        db.refresh(plugin)

        logger.info(
            "Plugin imported: %s (by %s)", plugin.name, current_user.username
        )

        return plugin.to_dict()

    except HTTPException:
        raise
    except (zipfile.BadZipFile, zipfile.LargeZipFile):
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except PluginFileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as e:
        logger.exception("Unexpected error importing plugin")
        raise HTTPException(status_code=500, detail="Plugin import failed") from e
