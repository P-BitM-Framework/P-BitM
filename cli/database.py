"""Database operations"""
import sqlite3
import re
import uuid
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timezone
from urllib.parse import quote
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text
import bcrypt

from cli.config import config
from cli.utils import error, warning, info, success

console = Console()
VALID_USER_ROLES = frozenset({"admin", "operator"})
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,63}$")


class AdminBootstrapState(str, Enum):
    """State of the configured administrator in the local database."""

    REQUIRED = "required"
    EXISTS = "exists"
    UNKNOWN = "unknown"


def _resolve_db_path(db_path=None) -> Path:
    """Resolve the configured database path from the project root."""
    path = Path(db_path) if db_path is not None else Path(
        config.get('database.path', './storage/p-bitm.db')
    )
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / path
    return path.resolve()


def _open_database_for_inspection(db_path: Path):
    """Open an existing SQLite database without permitting SQL writes."""
    database_uri = f"file:{quote(str(db_path), safe='/')}?mode=rw"
    connection = sqlite3.connect(
        database_uri,
        uri=True,
        timeout=1.0
    )
    connection.execute("PRAGMA query_only=ON")
    return connection


def get_admin_bootstrap_state(
    username: Optional[str] = None,
    db_path=None
) -> AdminBootstrapState:
    """
    Inspect whether the backend still needs to create the configured admin.

    UNKNOWN deliberately fails closed: callers must not display a password
    when the database cannot be inspected reliably.
    """
    username = username or config.get('admin.username', 'admin')
    resolved_path = _resolve_db_path(db_path)

    if not resolved_path.is_file():
        return AdminBootstrapState.REQUIRED

    connection = None
    try:
        connection = _open_database_for_inspection(resolved_path)
        users_table = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = 'users'
            LIMIT 1
            """
        ).fetchone()
        if not users_table:
            return AdminBootstrapState.REQUIRED

        admin = connection.execute(
            "SELECT 1 FROM users WHERE username = ? LIMIT 1",
            (username,)
        ).fetchone()
        return (
            AdminBootstrapState.EXISTS
            if admin
            else AdminBootstrapState.REQUIRED
        )
    except sqlite3.Error:
        return AdminBootstrapState.UNKNOWN
    finally:
        if connection is not None:
            connection.close()


def admin_password_matches(
    username: str,
    password: str,
    db_path=None
) -> Optional[bool]:
    """
    Check a runtime password against the stored administrator hash.

    Returns None while the user is not available or the database cannot be
    inspected, allowing the caller to retry during backend bootstrap.
    """
    resolved_path = _resolve_db_path(db_path)
    if not resolved_path.is_file():
        return None

    connection = None
    try:
        connection = _open_database_for_inspection(resolved_path)
        row = connection.execute(
            "SELECT password FROM users WHERE username = ? LIMIT 1",
            (username,)
        ).fetchone()
        if not row:
            return None

        stored_hash = row[0]
        if not stored_hash:
            return False

        return bcrypt.checkpw(
            password.encode('utf-8'),
            stored_hash.encode('utf-8')
        )
    except (sqlite3.Error, TypeError, ValueError):
        return None
    finally:
        if connection is not None:
            connection.close()


def get_db_connection():
    """Get database connection"""
    db_path = _resolve_db_path()

    if not db_path.exists():
        warning(f"Database not found at {db_path}")
        return None

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    except Exception as e:
        error(f"Failed to connect to database: {e}")
        return None


def finalize_campaigns_for_shutdown(db_path=None) -> bool:
    """Make every resumable campaign terminal after a global shutdown."""
    resolved_path = _resolve_db_path(db_path)
    if not resolved_path.is_file():
        info("No campaign database found; no runtime state needed updating")
        return True

    connection = None
    try:
        connection = sqlite3.connect(str(resolved_path), timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("BEGIN IMMEDIATE")

        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if "campaigns" not in tables:
            connection.commit()
            info("No campaign records found; no runtime state needed updating")
            return True

        terminalized_ids = [
            row[0]
            for row in connection.execute(
                """
                SELECT id
                FROM campaigns
                WHERE status IN ('active', 'paused', 'scheduled')
                """
            ).fetchall()
        ]
        if not terminalized_ids:
            connection.commit()
            info("No active, paused, or scheduled campaigns to complete")
            return True

        placeholders = ", ".join("?" for _ in terminalized_ids)
        if "victims" in tables:
            connection.execute(
                f"""
                UPDATE victims
                SET is_active = 0, container_status = 'stopped'
                WHERE campaign_id IN ({placeholders})
                """,
                terminalized_ids,
            )

        completed_at = (
            datetime.now(timezone.utc)
            .replace(tzinfo=None)
            .isoformat(sep=" ")
        )
        connection.execute(
            f"""
            UPDATE campaigns
            SET status = 'completed',
                container_status = 'stopped',
                completed_at = COALESCE(completed_at, ?)
            WHERE id IN ({placeholders})
            """,
            [completed_at, *terminalized_ids],
        )
        connection.commit()
        success(
            f"Completed {len(terminalized_ids)} campaign(s) after shutdown"
        )
        return True
    except sqlite3.Error as exc:
        if connection is not None:
            connection.rollback()
        error(f"Failed to finalize campaign state after shutdown: {exc}")
        return False
    finally:
        if connection is not None:
            connection.close()


def get_campaigns() -> List[Dict]:
    """Get all campaigns from database"""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                id,
                name,
                target_url,
                mode,
                protocol,
                created_at,
                status
            FROM campaigns
            ORDER BY created_at DESC
        """)

        campaigns = []
        for row in cursor.fetchall():
            campaigns.append(dict(row))

        return campaigns

    except Exception as e:
        error(f"Failed to fetch campaigns: {e}")
        return []
    finally:
        conn.close()


def get_campaign_by_id(campaign_id: str) -> Optional[Dict]:
    """Get single campaign by ID (supports partial ID matching)"""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor()

        # Try exact match first
        cursor.execute("""
            SELECT
                id,
                name,
                target_url,
                mode,
                protocol,
                created_at,
                updated_at,
                status
            FROM campaigns
            WHERE id = ?
        """, (campaign_id,))

        row = cursor.fetchone()

        # If not found, try partial match (first 8 chars)
        if not row:
            cursor.execute("""
                SELECT
                    id,
                    name,
                    target_url,
                    mode,
                    protocol,
                    created_at,
                    updated_at,
                    status
                FROM campaigns
                WHERE id LIKE ?
            """, (f"{campaign_id}%",))

            row = cursor.fetchone()

        return dict(row) if row else None

    except Exception as e:
        error(f"Failed to fetch campaign: {e}")
        return None
    finally:
        conn.close()


def get_victims(campaign_id: str = None) -> List[Dict]:
    """Get victims, optionally filtered by campaign"""
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()

        if campaign_id:
            # Try exact match
            cursor.execute("""
                SELECT
                    id,
                    campaign_id,
                    session_id,
                    ip_address,
                    user_agent,
                    is_active
                FROM victims
                WHERE campaign_id = ?
            """, (campaign_id,))

            victims = [dict(row) for row in cursor.fetchall()]

            # If no results, try partial match
            if not victims:
                cursor.execute("""
                    SELECT
                        id,
                        campaign_id,
                        session_id,
                        ip_address,
                        user_agent,
                        is_active
                    FROM victims
                    WHERE campaign_id LIKE ?
                """, (f"{campaign_id}%",))

                victims = [dict(row) for row in cursor.fetchall()]

            return victims
        else:
            cursor.execute("""
                SELECT
                    id,
                    campaign_id,
                    session_id,
                    ip_address,
                    user_agent,
                    is_active
                FROM victims
            """)

            return [dict(row) for row in cursor.fetchall()]

    except Exception as e:
        error(f"Failed to fetch victims: {e}")
        return []
    finally:
        conn.close()


def get_victim_by_id(campaign_id: str, victim_id: str) -> Optional[Dict]:
    """Get single victim by ID (supports partial ID matching)"""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor()

        # Try exact match
        cursor.execute("""
            SELECT
                id,
                campaign_id,
                session_id,
                ip_address,
                user_agent,
                is_active
            FROM victims
            WHERE id = ? AND (campaign_id = ? OR campaign_id LIKE ?)
        """, (victim_id, campaign_id, f"{campaign_id}%"))

        row = cursor.fetchone()

        # If not found, try partial victim ID match
        if not row:
            cursor.execute("""
                SELECT
                    id,
                    campaign_id,
                    session_id,
                    ip_address,
                    user_agent,
                    is_active,
                FROM victims
                WHERE id LIKE ? AND (campaign_id = ? OR campaign_id LIKE ?)
            """, (f"{victim_id}%", campaign_id, f"{campaign_id}%"))

            row = cursor.fetchone()

        return dict(row) if row else None

    except Exception as e:
        error(f"Failed to fetch victim: {e}")
        return None
    finally:
        conn.close()


def show_campaigns_table():
    """Display campaigns table"""
    campaigns = get_campaigns()

    if not campaigns:
        info("No campaigns found")
        console.print(f"\n[dim]Campaigns are created via the web dashboard at:[/]")
        dashboard_url = config.get('app.dashboard_url', 'https://127.0.0.1:8443/')
        console.print(f"[blue]{dashboard_url}[/]\n")
        return

    table = Table(
        title="Campaigns",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )

    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="yellow")
    table.add_column("Target URL", style="blue")
    table.add_column("Protocol", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Created", style="dim")

    for campaign in campaigns:
        # Color code status
        status = campaign.get('status', 'unknown')
        if status == 'active':
            status_str = "[green]● Active[/]"
        elif status == 'stopped':
            status_str = "[red]● Stopped[/]"
        else:
            status_str = f"[yellow]● {status}[/]"

        table.add_row(
            campaign.get('id', '')[:8],
            campaign.get('name', ''),
            campaign.get('target_url', ''),
            campaign.get('protocol', ''),
            status_str,
            campaign.get('created_at', '')
        )

    console.print()
    console.print(table)
    console.print(f"\n[dim]Total campaigns: {len(campaigns)}[/]")
    console.print(f"[dim]Use [bold]python3 p-bitm.py campaign <id> status[/] for details[/]\n")


def show_campaign_details(campaign_id: str):
    """Show detailed campaign information"""
    campaign = get_campaign_by_id(campaign_id)

    if not campaign:
        error(f"Campaign not found: {campaign_id}")
        return

    # Campaign info panel
    info_text = Text()
    info_text.append("Campaign ID: ", style="cyan")
    info_text.append(f"{campaign.get('id', 'N/A')}\n", style="white")

    info_text.append("Name: ", style="cyan")
    info_text.append(f"{campaign.get('name', 'N/A')}\n", style="yellow")

    info_text.append("Target URL: ", style="cyan")
    info_text.append(f"{campaign.get('target_url', 'N/A')}\n", style="blue")

    info_text.append("Protocol: ", style="cyan")
    info_text.append(f"{campaign.get('protocol', 'N/A')}\n", style="magenta")

    info_text.append("Mode: ", style="cyan")
    info_text.append(f"{campaign.get('mode', 'N/A')}\n", style="white")

    status = campaign.get('status', 'unknown')
    info_text.append("Status: ", style="cyan")
    if status == 'active':
        info_text.append("● Active\n", style="green")
    elif status == 'stopped':
        info_text.append("● Stopped\n", style="red")
    else:
        info_text.append(f"● {status}\n", style="yellow")

    info_text.append("Created: ", style="cyan")
    info_text.append(f"{campaign.get('created_at', 'N/A')}\n", style="dim")

    # if campaign.get('description'):
    #     info_text.append("\nDescription: ", style="cyan")
    #     info_text.append(f"{campaign.get('description')}", style="white")

    panel = Panel(
        info_text,
        title=f"[bold cyan]Campaign Details[/]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2)
    )

    console.print()
    console.print(panel)

    # Show victims for this campaign
    console.print()
    show_victims_table(campaign_id=campaign.get('id'))


def show_victims_table(campaign_id: str = None):
    """Display victims table"""
    victims = get_victims(campaign_id)

    if not victims:
        info(f"No victims found{' for campaign ' + campaign_id[:8] if campaign_id else ''}")
        return

    table = Table(
        title=f"Victims{' - Campaign: ' + campaign_id[:8] if campaign_id else ' (All Campaigns)'}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )

    table.add_column("Victim ID", style="cyan", no_wrap=True)
    if not campaign_id:
        table.add_column("Campaign", style="yellow", no_wrap=True)
    table.add_column("Container", style="magenta", no_wrap=True)
    table.add_column("IP Address", style="blue")
    table.add_column("Status", style="green")
    # table.add_column("Last Seen", style="dim")

    for victim in victims:
        # Color code status
        status = victim.get('is_active', 'unknown')
        if status == True:
            status_str = "[green]● Active[/]"
        elif status == False:
            status_str = "[yellow]● Inactive[/]"
        else:
            status_str = f"[red]● {status}[/]"

        row_data = [
            victim.get('id', '')[:8],
        ]

        if not campaign_id:
            row_data.append(victim.get('campaign_id', '')[:8])

        row_data.extend([
            victim.get('session_id', ''),
            victim.get('ip_address', ''),
            status_str
        ])

        table.add_row(*row_data)

    console.print(table)
    console.print(f"\n[dim]Total victims: {len(victims)}[/]\n")


def show_victim_details(campaign_id: str, victim_id: str):
    """Show detailed victim information"""
    victim = get_victim_by_id(campaign_id, victim_id)

    if not victim:
        error(f"Victim not found: {victim_id}")
        return

    # Victim info panel
    info_text = Text()
    info_text.append("Victim ID: ", style="cyan")
    info_text.append(f"{victim.get('id', 'N/A')}\n", style="white")

    info_text.append("Campaign ID: ", style="cyan")
    info_text.append(f"{victim.get('campaign_id', 'N/A')}\n", style="yellow")

    # info_text.append("Container ID: ", style="cyan")
    # info_text.append(f"{victim.get('container_id', 'N/A')}\n", style="magenta")

    info_text.append(f"{victim.get('ip_address', 'N/A')}\n", style="blue")

    info_text.append("User Agent: ", style="cyan")
    info_text.append(f"{victim.get('user_agent', 'N/A')}\n", style="dim")

    status = victim.get('is_active', 'unknown')
    info_text.append("Status: ", style="cyan")
    if status == 'active':
        info_text.append("● Active\n", style="green")
    elif status == 'inactive':
        info_text.append("● Inactive\n", style="yellow")
    else:
        info_text.append(f"● {status}\n", style="red")

    # info_text.append("Created: ", style="cyan")
    # info_text.append(f"{victim.get('created_at', 'N/A')}\n", style="dim")

    # info_text.append("Last Seen: ", style="cyan")
    # info_text.append(f"{victim.get('last_seen', 'N/A')}", style="dim")

    panel = Panel(
        info_text,
        title=f"[bold cyan]Victim Details[/]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2)
    )

    console.print()
    console.print(panel)
    console.print()


def dump_campaign_data(campaign_id: str, output_path: str = None):
    """Dump campaign data to JSON"""
    import json
    from datetime import datetime

    campaign = get_campaign_by_id(campaign_id)

    if not campaign:
        error(f"Campaign {campaign_id} not found")
        return False

    # Get victims
    victims = get_victims(campaign.get('id'))

    # Prepare data
    dump_data = {
        'campaign': campaign,
        'victims': victims,
        'victim_count': len(victims),
        'dumped_at': datetime.now().isoformat()
    }

    # Output path
    if not output_path:
        campaigns_dir = Path(config.get('paths.campaigns_dir', './storage/campaigns'))
        campaigns_dir.mkdir(parents=True, exist_ok=True)
        output_path = campaigns_dir / f"{campaign.get('id')[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    try:
        # Write JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dump_data, f, indent=2, ensure_ascii=False)

        success(f"Campaign data dumped to: {output_path}")
        info(f"Campaign: {campaign.get('name')}")
        info(f"Victims: {len(victims)}")
        return True

    except Exception as e:
        error(f"Failed to dump campaign data: {e}")
        return False

def hash_password(password: str) -> str:
    """Hash password with bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def _revoke_user_sessions_if_available(conn, user_id: str) -> None:
    """Revoke sessions while remaining compatible with pre-migration databases."""
    sessions_table = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = 'user_sessions'
        LIMIT 1
        """
    ).fetchone()
    if sessions_table:
        conn.execute(
            "DELETE FROM user_sessions WHERE user_id = ?",
            (user_id,),
        )


def generate_secure_password(length: int = 32) -> str:
    """Generate a secure random hex password for admin (default 32 chars = 128 bit)"""
    import secrets
    return secrets.token_hex(length // 2)

def reset_admin_password(username: str, new_password: str):
    """Reset a user's password in the database."""
    conn = get_db_connection()
    if not conn:
        return False

    password_hash = hash_password(new_password)

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        user = cursor.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if not user:
            warning(f"User not found: {username}")
            conn.rollback()
            return False

        cursor.execute("""
            UPDATE users
            SET password = ?
            WHERE id = ?
        """, (password_hash, user["id"]))
        _revoke_user_sessions_if_available(conn, user["id"])

        conn.commit()
        success(f"Password reset for user: {username}")
        return True

    except Exception as e:
        error(f"Failed to reset admin password: {e}")
        return False
    finally:
        conn.close()


def get_users() -> List[Dict]:
    """Return local users for CLI administration."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        rows = conn.execute(
            """
            SELECT id, username, email, role, is_active, created_at, last_login
            FROM users
            ORDER BY
                CASE role WHEN 'admin' THEN 0 ELSE 1 END,
                username COLLATE NOCASE
            """
        ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        error(f"Failed to fetch users: {exc}")
        return []
    finally:
        conn.close()


def create_local_user(
    username: str,
    email: str,
    password: str,
    role: str = "operator",
) -> bool:
    username = username.strip()
    email = email.strip()
    if not USERNAME_PATTERN.fullmatch(username):
        error(
            "Username must be 3-64 characters and contain only letters, "
            "numbers, dots, dashes, or underscores"
        )
        return False
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        error("A valid email address is required")
        return False
    if role not in VALID_USER_ROLES:
        error("Role must be admin or operator")
        return False
    if len(password) < 12:
        error("Password must be at least 12 characters long")
        return False

    conn = get_db_connection()
    if not conn:
        return False
    try:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute(
            "SELECT 1 FROM users WHERE username = ? OR email = ? LIMIT 1",
            (username, email),
        ).fetchone():
            error("Username or email already exists")
            conn.rollback()
            return False
        conn.execute(
            """
            INSERT INTO users (
                id, username, email, password, role, created_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                str(uuid.uuid4())[:8],
                username,
                email,
                hash_password(password),
                role,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        success(f"Created {role}: {username}")
        return True
    except sqlite3.Error as exc:
        conn.rollback()
        error(f"Failed to create user: {exc}")
        return False
    finally:
        conn.close()


def set_local_user_role(username: str, role: str) -> bool:
    if role not in VALID_USER_ROLES:
        error("Role must be admin or operator")
        return False
    conn = get_db_connection()
    if not conn:
        return False
    try:
        conn.execute("BEGIN IMMEDIATE")
        user = conn.execute(
            "SELECT id, role, is_active FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if not user:
            warning(f"User not found: {username}")
            conn.rollback()
            return False
        if user["role"] == "admin" and role != "admin" and user["is_active"]:
            active_admins = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
            ).fetchone()[0]
            if active_admins <= 1:
                error("Cannot demote the last active admin user")
                conn.rollback()
                return False
        conn.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            (role, user["id"]),
        )
        _revoke_user_sessions_if_available(conn, user["id"])
        conn.commit()
        success(f"Updated {username} role to {role}")
        return True
    except sqlite3.Error as exc:
        conn.rollback()
        error(f"Failed to update role: {exc}")
        return False
    finally:
        conn.close()


def set_local_user_active(username: str, is_active: bool) -> bool:
    configured_admin = config.get("admin.username", "admin")
    if username == configured_admin and not is_active:
        error("Cannot disable the configured administrator")
        return False

    conn = get_db_connection()
    if not conn:
        return False
    try:
        conn.execute("BEGIN IMMEDIATE")
        user = conn.execute(
            "SELECT id, role, is_active FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if not user:
            warning(f"User not found: {username}")
            conn.rollback()
            return False
        if user["role"] == "admin" and user["is_active"] and not is_active:
            active_admins = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
            ).fetchone()[0]
            if active_admins <= 1:
                error("Cannot disable the last active admin user")
                conn.rollback()
                return False
        conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (int(is_active), user["id"]),
        )
        _revoke_user_sessions_if_available(conn, user["id"])
        conn.commit()
        success(f"{'Enabled' if is_active else 'Disabled'} user: {username}")
        return True
    except sqlite3.Error as exc:
        conn.rollback()
        error(f"Failed to update user access: {exc}")
        return False
    finally:
        conn.close()


def delete_local_user(username: str) -> bool:
    configured_admin = config.get("admin.username", "admin")
    if username == configured_admin:
        error("Cannot delete the configured administrator")
        return False

    conn = get_db_connection()
    if not conn:
        return False
    try:
        conn.execute("BEGIN IMMEDIATE")
        user = conn.execute(
            "SELECT id, role, is_active FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        admin = conn.execute(
            """
            SELECT id FROM users
            WHERE username = ? AND role = 'admin' AND is_active = 1
            """,
            (configured_admin,),
        ).fetchone()
        if not user:
            warning(f"User not found: {username}")
            conn.rollback()
            return False
        if not admin:
            error("Configured active administrator not found")
            conn.rollback()
            return False
        if user["role"] == "admin" and user["is_active"]:
            active_admins = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
            ).fetchone()[0]
            if active_admins <= 1:
                error("Cannot delete the last active admin user")
                conn.rollback()
                return False
        reassigned = conn.execute(
            "UPDATE campaigns SET created_by = ? WHERE created_by = ?",
            (admin["id"], user["id"]),
        ).rowcount
        _revoke_user_sessions_if_available(conn, user["id"])
        conn.execute("DELETE FROM users WHERE id = ?", (user["id"],))
        conn.commit()
        success(
            f"Deleted user: {username}"
            + (f" ({reassigned} campaign(s) reassigned)" if reassigned else "")
        )
        return True
    except sqlite3.Error as exc:
        conn.rollback()
        error(f"Failed to delete user: {exc}")
        return False
    finally:
        conn.close()
