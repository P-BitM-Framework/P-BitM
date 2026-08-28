from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import case, func
from database import SessionLocal
from models import Campaign, Victim, EmailTemplate, SMTPProfile, VictimStatus, CampaignStatus
from utils.campaign_domains import find_public_domain_conflict
from utils.email_sender import EmailSender
from utils.docker import CampaignRuntimeStateError, set_campaign_runtime_started
import logging
import time

logger = logging.getLogger(__name__)


def campaign_is_active(db: Session, campaign_id: str) -> bool:
    """Read the current persisted status before sending another email."""
    status = db.query(Campaign.status).filter(
        Campaign.id == campaign_id
    ).scalar()
    return status == CampaignStatus.active


def activate_scheduled_campaigns(db: Session, now: datetime) -> int:
    """Start due runtimes before making scheduled campaigns available."""
    campaigns = db.query(Campaign).filter(
        Campaign.status == CampaignStatus.scheduled,
        Campaign.campaign_type == "full",
        Campaign.scheduled_start <= now,
    ).all()

    activated = 0
    for campaign in campaigns:
        domain_conflict = find_public_domain_conflict(
            db,
            campaign.public_url,
            exclude_campaign_id=campaign.id,
        )
        if domain_conflict is not None:
            logger.warning(
                "Scheduled campaign %s is waiting for public domain held by %s",
                campaign.id,
                domain_conflict.id,
            )
            continue

        campaign.status = CampaignStatus.active
        campaign.container_status = "starting"
        if campaign.started_at is None:
            campaign.started_at = now
        db.commit()

        try:
            set_campaign_runtime_started(
                campaign.container_name,
                campaign.id,
                True,
            )
        except CampaignRuntimeStateError:
            db.rollback()
            campaign = db.query(Campaign).filter(
                Campaign.id == campaign.id
            ).first()
            if campaign is not None:
                campaign.status = CampaignStatus.scheduled
                campaign.container_status = "start_failed"
                campaign.started_at = None
                db.commit()
            logger.exception(
                "Scheduled campaign %s could not be activated; retrying later",
                campaign.id if campaign is not None else "unknown",
            )
            continue

        campaign.container_status = "running"
        db.commit()
        activated += 1
        logger.info("Activated scheduled campaign: %s", campaign.name)

    return activated


def check_and_send_emails():
    """
    Background job that runs every minute.
    Checks scheduled campaigns and victims ready for sending.
    """
    db = SessionLocal()
    try:
        # 1. Start scheduled campaigns
        now = datetime.now(timezone.utc)
        activate_scheduled_campaigns(db, now)

        # 2. Send emails for ready victims
        active_campaigns = db.query(Campaign).filter(
            Campaign.status == CampaignStatus.active,
            Campaign.campaign_type == "full",
        ).all()

        for campaign in active_campaigns:
            send_campaign_batch(db, campaign)

    except Exception:
        db.rollback()
        logger.exception("Email scheduler failed")
    finally:
        db.close()


def send_campaign_batch(db: Session, campaign: Campaign):
    """
    Send a batch of emails for a given campaign.
    This function is called by the background job for each active campaign.
    """

    # Standalone campaigns create victims for browser sessions but intentionally
    # have no email template or SMTP profile.
    if campaign.campaign_type != "full":
        return
    if not campaign_is_active(db, campaign.id):
        return

    # Get victims ready to send (scheduled_send_at <= now)
    now = datetime.now(timezone.utc)
    victims = db.query(Victim).filter(
        Victim.campaign_id == campaign.id,
        Victim.status == VictimStatus.pending,
        Victim.scheduled_send_at <= now
    ).limit(50).all()

    if not victims:
        return

    logger.info(f"📧 Sending {len(victims)} emails for campaign: {campaign.name}")

    # Get email template
    template = db.query(EmailTemplate).filter(
        EmailTemplate.id == campaign.email_template_id
    ).first()

    if not template:
        logger.error(f"❌ Template {campaign.email_template_id} not found")
        return

    # Get SMTP profile
    smtp_profile = db.query(SMTPProfile).filter(
        SMTPProfile.id == campaign.sending_profile_id
    ).first()

    if not smtp_profile:
        logger.error(f"❌ SMTP profile {campaign.sending_profile_id} not found")
        return

    # ✅ Use EmailSender with persistent connection
    sender = EmailSender(smtp_profile)
    success, message = sender.connect()

    if not success:
        logger.error(f"❌ Failed to connect to SMTP: {message}")
        return

    try:
        # Base tracking URL (usa il public_url della campaign)
        campaign_url = campaign.public_url.rstrip('/')
        advanced_options = campaign.advanced_options or {}
        routes = advanced_options.get("routes")
        entry_path = (
            routes.get("entry_path", "")
            if isinstance(routes, dict)
            else "continue"
        )
        tracking_parameter = (
            routes.get("tracking_parameter")
            if isinstance(routes, dict)
            else None
        )

        # Send emails con rate limiting
        for victim in victims:
            if not campaign_is_active(db, campaign.id):
                logger.info(
                    "Campaign %s paused; stopping the active email batch",
                    campaign.id,
                )
                break
            try:
                # ✅ Use your EmailSender class
                success, error_msg = sender.send_phishing_email(
                    victim=victim,
                    template=template,
                    campaign_url=campaign_url,
                    entry_path=entry_path,
                    tracking_parameter=tracking_parameter,
                )

                if success:
                    # Update victim
                    victim.status = VictimStatus.email_sent
                    victim.email_sent_at = datetime.now(timezone.utc)
                    logger.info(f"✅ Email sent to {victim.email}")
                else:
                    # Email failed
                    victim.status = VictimStatus.error
                    victim.error_message = error_msg[:500]
                    logger.error(f"❌ Failed to send to {victim.email}: {error_msg}")

                db.commit()

                # Rate limiting: 1 email al secondo
                time.sleep(1)

            except Exception:
                logger.exception(
                    "Unexpected email delivery failure for %s",
                    victim.email,
                )
                # A failed db.commit() above would otherwise leave the
                # session unusable for this recovery write.
                db.rollback()
                victim.status = VictimStatus.error
                victim.error_message = "Unexpected email delivery failure"
                db.commit()

        # Update campaign stats
        update_campaign_stats(db, campaign.id)

    finally:
        # ✅ Close persistent connection
        sender.disconnect()


def update_campaign_stats(db: Session, campaign_id: str):
    """Update campaign email statistics"""

    stats = db.query(
        func.count(Victim.id).label('total'),
        func.sum(case((Victim.email_sent_at.isnot(None), 1), else_=0)).label('sent'),
        func.sum(case((Victim.email_opened_at.isnot(None), 1), else_=0)).label('opened'),
        func.sum(case((Victim.email_link_clicked_at.isnot(None), 1), else_=0)).label('clicked'),
        func.sum(case((Victim.data_submitted_at.isnot(None), 1), else_=0)).label('submitted')
    ).filter(Victim.campaign_id == campaign_id).first()

    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if campaign:
        campaign.emails_sent = stats.sent or 0
        campaign.emails_opened = stats.opened or 0
        campaign.links_clicked = stats.clicked or 0
        campaign.data_submitted = stats.submitted or 0
        db.commit()
