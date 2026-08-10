# campaign-container/app/routes/tracking.py

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session
from utils.tracking import update_victim_opened, update_victim_clicked, update_victim_submitted
from database import get_db
from routes.auth import verify_tracking_internal_key
from models import Victim
from utils.request_models import TrackingEventRequest
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# ✅ Tracking Pixel - Email Opened
@router.post("/email-opened")
async def track_email_open(
    data: TrackingEventRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_tracking_internal_key)
):
    """Track when victim opens email"""
    try:
        tracking_id = data.tracking_id

        logger.info("Processing email-open tracking callback")

        if not tracking_id:
            raise HTTPException(status_code=400, detail="Missing tracking_id")

        victim = db.query(Victim).filter(Victim.tracking_id == tracking_id).first()
        if not victim:
            logger.warning("Tracking callback did not match a victim")
            raise HTTPException(status_code=404, detail="Victim not found")

        update_victim_opened(
            db=db,
            victim=victim,
            ip_address=data.ip_address,
            user_agent=data.user_agent,
        )

        logger.info("Email-open event recorded for victim %s", victim.id)

        return JSONResponse(content=victim.to_dict(), status_code=200)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to record email-open tracking event")
        raise HTTPException(
            status_code=500,
            detail="Unable to record email-open event",
        ) from exc


# ✅ Tracking Link - Link Clicked
@router.post("/link-clicked")
async def track_link_click(
    data: TrackingEventRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_tracking_internal_key)
):
    """Track when victim clicks link"""
    try:
        tracking_id = data.tracking_id

        logger.info("Processing link-click tracking callback")

        if not tracking_id:
            raise HTTPException(status_code=400, detail="Missing tracking_id")

        victim = db.query(Victim).filter(Victim.tracking_id == tracking_id).first()
        if not victim:
            logger.warning("Tracking callback did not match a victim")
            raise HTTPException(status_code=404, detail="Victim not found")

        update_victim_clicked(
            db=db,
            victim=victim,
            ip_address=data.ip_address,
            user_agent=data.user_agent,
        )

        logger.info("Link-click event recorded for victim %s", victim.id)

        return JSONResponse(content=victim.to_dict(), status_code=200)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to record link-click tracking event")
        raise HTTPException(
            status_code=500,
            detail="Unable to record link-click event",
        ) from exc


# ✅ Form Submission - Data Submitted
@router.post("/data-submitted")
async def track_data_submit(
    data: TrackingEventRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_tracking_internal_key)
):
    """Track when victim submits form data"""
    try:
        tracking_id = data.tracking_id
        submitted_data = data.submitted_data or {}

        logger.info("Processing data-submission tracking callback")

        if not tracking_id:
            raise HTTPException(status_code=400, detail="Missing tracking_id")

        victim = db.query(Victim).filter(Victim.tracking_id == tracking_id).first()
        if not victim:
            logger.warning("Tracking callback did not match a victim")
            raise HTTPException(status_code=404, detail="Victim not found")

        update_victim_submitted(
            db=db,
            victim=victim,
            submitted_data=submitted_data
        )

        logger.info("Data-submission event recorded for victim %s", victim.id)

        return Response(status_code=200)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to record data-submission tracking event")
        raise HTTPException(
            status_code=500,
            detail="Unable to record data-submission event",
        ) from exc
