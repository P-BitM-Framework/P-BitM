# routes/landing_pages.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import uuid
import logging
from datetime import datetime, timezone

from database import get_db
from models import LandingPage, User
from routes.auth import get_current_user_from_session, require_operator
from pydantic import BaseModel, ConfigDict, Field
from utils.uploads import (
    UploadValidationError,
    configured_upload_limit,
    read_upload_limited,
    validate_transfer_filename,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# Schemas
class LandingPageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    content: str = Field(default="", max_length=5 * 1024 * 1024)


class LandingPageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    content: str | None = Field(default=None, max_length=5 * 1024 * 1024)


# Get all landing pages
@router.get("")
async def get_landing_pages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    pages = db.query(LandingPage).all()
    return {
        "landing_pages": [page.to_dict() for page in pages]
    }


# Get single landing page
@router.get("/{page_id}")
async def get_landing_page(
    page_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    page = db.query(LandingPage).filter(LandingPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Landing page not found")

    return page.to_dict()


# Create landing page
@router.post("")
async def create_landing_page(
    data: LandingPageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    page = LandingPage(
        name=data.name,
        description=data.description,
        content=data.content,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db.add(page)
    db.commit()
    db.refresh(page)

    logger.info("Landing page created: %s (by %s)", page.name, current_user.username)

    return page.to_dict()


# Update landing page
@router.put("/{page_id}")
async def update_landing_page(
    page_id: str,
    data: LandingPageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    page = db.query(LandingPage).filter(LandingPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Landing page not found")

    if data.name is not None:
        page.name = data.name
    if data.description is not None:
        page.description = data.description
    if data.content is not None:
        page.content = data.content

    page.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(page)

    logger.info("Landing page updated: %s (by %s)", page.name, current_user.username)

    return page.to_dict()


# Delete landing page
@router.delete("/{page_id}")
async def delete_landing_page(
    page_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    page = db.query(LandingPage).filter(LandingPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Landing page not found")

    db.delete(page)
    db.commit()

    logger.info("Landing page deleted: %s (by %s)", page.name, current_user.username)

    return {"message": "Landing page deleted successfully"}


# Export landing page as HTML file
@router.get("/{page_id}/export")
async def export_landing_page(
    page_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_session)
):
    from fastapi.responses import Response

    page = db.query(LandingPage).filter(LandingPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Landing page not found")

    # Sanitize filename
    safe_name = "".join(c for c in page.name if c.isalnum() or c in (' ', '-', '_')).strip()

    return Response(
        content=page.content,
        media_type="text/html",
        headers={
            "Content-Disposition": f"attachment; filename={safe_name}.html"
        }
    )


# Clone landing page
@router.post("/{page_id}/clone")
async def clone_landing_page(
    page_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    original = db.query(LandingPage).filter(LandingPage.id == page_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Landing page not found")

    cloned = LandingPage(
        name=f"{original.name} (Copy)",
        description=original.description,
        content=original.content,
        created_at=datetime.now(timezone.utc)
    )

    db.add(cloned)
    db.commit()
    db.refresh(cloned)

    logger.info(
        "Landing page cloned: %s -> %s (by %s)",
        original.name,
        cloned.name,
        current_user.username,
    )

    return cloned.to_dict()


# Import from HTML file
@router.post("/import")
async def import_landing_page(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_operator)
):
    try:
        safe_filename = validate_transfer_filename(file.filename)
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not safe_filename.lower().endswith('.html'):
        raise HTTPException(status_code=400, detail="Only HTML files are supported")

    try:
        content = await read_upload_limited(
            file,
            configured_upload_limit(
                "MAX_LANDING_PAGE_UPLOAD_BYTES",
                5 * 1024 * 1024,
            ),
        )
        html_content = content.decode('utf-8')

        # Extract title from HTML if present
        import re
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        page_name = (
            title_match.group(1).strip()
            if title_match
            else safe_filename[:-5]
        )
        page_name = page_name[:255] or "Imported landing page"

        page = LandingPage(
            name=page_name,
            description="Imported landing page",
            content=html_content,
            created_at=datetime.now(timezone.utc)
        )

        db.add(page)
        db.commit()
        db.refresh(page)

        logger.info(
            "Landing page imported: %s (by %s)", page.name, current_user.username
        )

        return page.to_dict()

    except UploadValidationError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="The HTML file must use UTF-8 encoding",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Landing page import failed")
        raise HTTPException(status_code=500, detail="Import failed") from exc
