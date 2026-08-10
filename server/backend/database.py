# admin-backend/database.py
import os
from pathlib import Path
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, declarative_base
import logging


logger = logging.getLogger(__name__)


# Runtime paths
STORAGE_PATH = Path(os.getenv("STORAGE_PATH", "/storage"))
DB_PATH = STORAGE_PATH / "p-bitm.db"


STORAGE_PATH.mkdir(parents=True, exist_ok=True)


engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={
        "check_same_thread": False,
        "timeout": 30.0,
        "isolation_level": None,
    },
    poolclass=pool.NullPool,
    echo=False,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, _connection_record):
    """Configure every SQLite connection for durability and concurrency."""
    cursor = dbapi_conn.cursor()

    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=FULL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA locking_mode=NORMAL")
    cursor.execute("PRAGMA secure_delete=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create a fresh schema and ensure that the administrator exists."""
    from models import (
        User,
        UserSession,
        Campaign,
        Victim,
        DataCollection,
        Target,
        TargetList,
        EmailTemplate,
        SMTPProfile
    )
    from utils.auth import hash_password
    from schema_migrations import apply_schema_migrations
    import uuid

    # create_all is only used for a fresh database. Released schema upgrades
    # must use ordered migrations instead of startup-time ALTER statements.
    Base.metadata.create_all(bind=engine)
    apply_schema_migrations(engine)
    logger.info(f"✅ Database schema created at {DB_PATH}")

    # Create default admin user
    db = SessionLocal()
    try:
        admin_username = os.getenv("ADMIN_USERNAME", "admin")

        legacy_viewers = db.query(User).filter(User.role == "viewer").all()
        reassigned_campaign_ids = []
        for legacy_viewer in legacy_viewers:
            campaign_ids = [
                campaign_id
                for (campaign_id,) in db.query(Campaign.id).filter(
                    Campaign.created_by == legacy_viewer.id
                ).all()
            ]
            reassigned_campaign_ids.extend(campaign_ids)
            if campaign_ids:
                db.query(Campaign).filter(
                    Campaign.id.in_(campaign_ids)
                ).update(
                    {Campaign.created_by: None},
                    synchronize_session=False,
                )
            db.delete(legacy_viewer)
        if legacy_viewers:
            db.flush()
            logger.warning(
                "Deleted %s legacy viewer account(s)",
                len(legacy_viewers),
            )

        admin = db.query(User).filter_by(username=admin_username).first()

        if not admin:
            admin_password = os.environ["ADMIN_PASSWORD"]
            admin_email = os.getenv("ADMIN_EMAIL", "admin@bitm.local")

            admin = User(
                id=str(uuid.uuid4())[:8],
                username=admin_username,
                email=admin_email,
                password=hash_password(admin_password),
                role="admin",
                is_active=True
            )

            db.add(admin)
            db.flush()

            logger.info(f"✅ Admin user created: {admin_username}")
            logger.warning("⚠️  Change the initial administrator password after first login.")
        else:
            logger.info(f"✅ Admin user already exists: {admin.username}")

        if reassigned_campaign_ids:
            db.query(Campaign).filter(
                Campaign.id.in_(reassigned_campaign_ids)
            ).update(
                {Campaign.created_by: admin.id},
                synchronize_session=False,
            )
            logger.warning(
                "Reassigned %s legacy campaign(s) to the administrator",
                len(reassigned_campaign_ids),
            )

        db.commit()

    except Exception:
        db.rollback()
        logger.exception("Failed to initialize the administrator")
        raise
    finally:
        db.close()
