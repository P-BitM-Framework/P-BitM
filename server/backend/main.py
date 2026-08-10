"""Admin control-plane application entry point."""

import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import Depends, FastAPI

from database import init_db
from routes import (
    auth_router,
    campaigns_router,
    email_templates_router,
    landing_pages_router,
    modules_router,
    plugins_router,
    sending_profiles_router,
    target_lists_router,
    tracking_router,
    users_router,
)
from routes.auth import require_operator
from services.artifact_reconciler import reconcile_persisted_artifacts
from services.email_sender import check_and_send_emails
from services.runtime_reconciler import reconcile_campaign_runtime
from utils.body_limit import RequestBodyLimitMiddleware
from utils.runtime_security import validate_runtime_security
from utils.secret_storage import migrate_legacy_smtp_secrets


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# The process owns one scheduler shared by the application lifespan.
scheduler = AsyncIOScheduler()


def configure_scheduler(target: AsyncIOScheduler) -> None:
    """Register idempotent control-plane background jobs."""
    target.add_job(
        check_and_send_emails,
        trigger=IntervalTrigger(minutes=1),
        id="email_sender",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=30,
    )
    target.add_job(
        reconcile_campaign_runtime,
        trigger=IntervalTrigger(minutes=5),
        id="runtime_reconciler",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )


def seed_initial_data() -> None:
    """Seed bundled resources when explicitly enabled."""
    if os.getenv("SEED_DATA", "false").lower() != "true":
        return

    from seed_data import seed_all

    logger.info("Seeding bundled resources")
    seed_all()
    logger.info("Bundled resources seeded")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize persistent state and background jobs."""
    logger.info("Starting p-bitm admin backend")
    validate_runtime_security()
    init_db()
    logger.info("Database initialized")

    reconcile_persisted_artifacts()
    migrated_secrets = migrate_legacy_smtp_secrets()
    if migrated_secrets:
        logger.info("Encrypted %s legacy SMTP secret(s)", migrated_secrets)

    seed_initial_data()
    configure_scheduler(scheduler)
    scheduler.start()
    logger.info("Admin backend ready")

    try:
        yield
    finally:
        logger.info("Stopping p-bitm admin backend")
        if scheduler.running:
            scheduler.shutdown(wait=True)
        logger.info("Admin backend stopped")


app = FastAPI(
    title="BITM Admin Backend",
    version="2.0",
    lifespan=lifespan,
)
app.add_middleware(
    RequestBodyLimitMiddleware,
    max_bytes=12 * 1024 * 1024,
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(
    campaigns_router,
    prefix="/api/campaigns",
    tags=["campaigns"],
)
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(
    sending_profiles_router,
    prefix="/api/sending-profiles",
    tags=["sending-profiles"],
)
app.include_router(
    email_templates_router,
    prefix="/api/email-templates",
    tags=["email-templates"],
)
app.include_router(
    target_lists_router,
    prefix="/api/target-lists",
    tags=["target-lists"],
)
app.include_router(
    tracking_router,
    prefix="/api/tracking",
    tags=["tracking"],
)
app.include_router(plugins_router, prefix="/api/plugins", tags=["plugins"])
app.include_router(
    landing_pages_router,
    prefix="/api/landing-pages",
    tags=["landing-pages"],
)
app.include_router(modules_router, prefix="/api/modules", tags=["modules"])


@app.get("/health")
async def health_check():
    """Report admin backend process health."""
    return {
        "status": "healthy",
        "service": "admin-backend",
        "scheduler_running": scheduler.running,
    }


@app.get("/scheduler/status")
async def scheduler_status(_current_user=Depends(require_operator)):
    """Return scheduler state for an authenticated operator."""
    jobs = [
        {
            "id": job.id,
            "next_run": (
                job.next_run_time.isoformat()
                if job.next_run_time
                else None
            ),
            "trigger": str(job.trigger),
        }
        for job in scheduler.get_jobs()
    ]
    return {"running": scheduler.running, "jobs": jobs}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8443,
        log_level="info",
    )
