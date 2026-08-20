"""CLI command handlers"""
import sys
import json
import subprocess
import time
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from cli.config import config
from cli.utils import (
    generate_env_file, success, error, warning, info,
    get_local_ip, generate_ssl_certs, update_env_file,
    cleanup_victim_containers, cleanup_campaign_containers,
    remove_all_images, ensure_dns_challenge, show_admin_credentials,
    ensure_storage_directories, read_env_file, StorageOwnershipError
)
from cli.doctor import CheckStatus, DoctorRunner
from cli.docker_ops import (
    check_docker, compose_up, compose_stop, compose_down, get_status_data,
    show_status, get_campaign_container_logs,
    get_victim_container_logs, start_campaign_container,
    stop_campaign_container, start_victim_container,
    stop_victim_container
)
from cli.database import (
    AdminBootstrapState, admin_password_matches, get_admin_bootstrap_state,
    finalize_campaigns_for_shutdown,
    get_campaigns, get_campaign_by_id, get_victims, get_victim_by_id,
    show_campaigns_table, show_campaign_details, show_victims_table,
    show_victim_details, dump_campaign_data, get_users, create_local_user,
    set_local_user_role, set_local_user_active, delete_local_user
)

console = Console()


def _show_initial_admin_credentials(timeout=15.0, poll_interval=0.25):
    """
    Display the initial credentials only after the backend persisted them.

    Verifying the password against the stored hash prevents an old value from
    server/.env being shown after an administrator changed their password.
    """
    env_values = read_env_file()
    username = env_values.get(
        'ADMIN_USERNAME',
        config.get('admin.username', 'admin')
    )
    password = env_values.get('ADMIN_PASSWORD')

    if not password:
        warning(
            "The initial administrator was not verified because "
            "ADMIN_PASSWORD is missing from server/.env."
        )
        return False

    deadline = time.monotonic() + timeout
    verified = False
    mismatch = False
    with console.status(
        "[bold cyan]Waiting for initial administrator bootstrap...",
        spinner="dots"
    ):
        while time.monotonic() < deadline:
            password_matches = admin_password_matches(username, password)
            if password_matches is True:
                verified = True
                break
            if password_matches is False:
                mismatch = True
                break
            time.sleep(poll_interval)

    if verified:
        show_admin_credentials(username, password)
        return True
    if mismatch:
        warning(
            "The administrator was created with different credentials; "
            "the runtime password will not be displayed."
        )
        return False

    warning(
        "The administrator was not created within the expected time. "
        "Check backend logs or reset the password with "
        "`python3 p-bitm.py admin reset-password`."
    )
    return False


# =============================================================================
# GLOBAL COMMANDS
# =============================================================================

def cmd_setup(rotate_dns_secrets=False, prerequisites_checked=False):
    """Initial setup: generate certs, create directories"""
    # The command dispatcher already rendered the banner when needed.

    console.print("\n[bold cyan]🔧 Running initial setup...[/]\n")

    # Check Docker
    if not prerequisites_checked and not check_docker():
        error(
            "Install the required Docker Engine and CLI plugins, then "
            "rerun setup."
        )
        return False

    try:
        storage_dir, campaigns_dir = ensure_storage_directories()
    except (OSError, StorageOwnershipError) as exc:
        error(f"Storage preflight failed: {exc}")
        return False

    # Get IP
    if config.get('network.auto_detect_ip', True):
        ip = get_local_ip()
        info(f"Detected IP: {ip}")
    else:
        ip = config.get('network.static_ip', '127.0.0.1')
        info(f"Using static IP: {ip}")

    # Provision production secrets before regenerating .env so installations
    # using the legacy DuckDNS layout are migrated safely.
    if (
        config.get('app.environment', 'production') == 'production'
        and not ensure_dns_challenge(force=rotate_dns_secrets)
    ):
        return False

    # Update generated runtime configuration
    generate_env_file()
    update_env_file(ip)

    # Create non-storage runtime directories. Storage was validated before any
    # secrets or generated configuration were written.
    certs_dir = Path(config.get('paths.certs_dir', './certs'))
    letsencrypt_dir = certs_dir / 'letsencrypt'

    for directory in [certs_dir, letsencrypt_dir]:
        directory.mkdir(parents=True, exist_ok=True)
        directory.chmod(0o755)
        info(f"Created directory: {directory}")
    for directory in [storage_dir, campaigns_dir]:
        info(f"Created directory: {directory}")

    # Generate SSL certificates
    if config.get('ssl.auto_generate', True):
        cert_path = certs_dir / 'cert.pem'
        key_path = certs_dir / 'key.pem'

        if cert_path.is_symlink() or key_path.is_symlink():
            error("Refusing to use symlinked TLS certificate files")
            return False
        invalid_paths = [
            path for path in (cert_path, key_path)
            if path.exists() and not path.is_file()
        ]
        if invalid_paths:
            error(
                "TLS certificate path is not a regular file: "
                + ", ".join(str(path) for path in invalid_paths)
            )
            return False

        if cert_path.exists() and key_path.exists():
            info("SSL certificates already exist")
        else:
            console.print("\n[cyan]Generating SSL certificates...[/]")
            common_name = config.get('ssl.common_name', ip)
            if generate_ssl_certs(common_name, str(cert_path), str(key_path)):
                success("SSL certificates generated")
            else:
                error("Failed to generate SSL certificates")
                return False
        cert_path.chmod(0o644)
        key_path.chmod(0o600)

    success("\n✅ Setup completed successfully!")
    if get_admin_bootstrap_state() == AdminBootstrapState.REQUIRED:
        info(
            "Initial admin credentials will be displayed after the first "
            "successful service start."
        )
    console.print(f"\n[dim]Next step: Run [bold]python3 p-bitm.py up[/] to start services[/]")

    return True


def cmd_up(build=False):
    """Start services"""
    # The command dispatcher already rendered the banner.

    if not check_docker():
        return False

    try:
        ensure_storage_directories()
    except (OSError, StorageOwnershipError) as exc:
        error(f"Storage preflight failed: {exc}")
        return False

    admin_state_before_start = get_admin_bootstrap_state()

    # Run setup once when runtime prerequisites are missing. The database is
    # initialized by the backend container, not by setup.
    certs_dir = Path(config.get('paths.certs_dir', './certs'))
    env_file = Path(config.get('paths.env_file', './server/.env'))
    if not env_file.exists() or not (certs_dir / 'cert.pem').exists():
        warning("Runtime configuration is incomplete, running setup first...")
        console.print()  # Spacing
        if not cmd_setup(prerequisites_checked=True):
            return False
    else:
        if (
            config.get('app.environment', 'production') == 'production'
            and not ensure_dns_challenge()
        ):
            return False

        # Reconcile non-secret runtime values on every start while preserving
        # generated credentials.
        ip = (
            get_local_ip()
            if config.get('network.auto_detect_ip', True)
            else config.get('network.static_ip', '127.0.0.1')
        )
        generate_env_file()
        update_env_file(ip)

    started = compose_up(build=build)
    if not started:
        return False

    if admin_state_before_start == AdminBootstrapState.REQUIRED:
        _show_initial_admin_credentials()
    elif admin_state_before_start == AdminBootstrapState.UNKNOWN:
        warning(
            "The administrator database could not be inspected before startup; "
            "credentials were not displayed automatically."
        )

    return True


def cmd_down(volumes=False):
    """Terminate all P-BitM services and dynamic campaign workloads."""
    if volumes and config.get('cli.confirm_destructive', True):
        if not Confirm.ask("⚠️  This will delete all data. Continue?"):
            info("Cancelled")
            return False

    console.print("\n[cyan]🛑 Terminating all P-BitM workloads...[/]")

    control_plane_stopped = compose_stop()
    campaign_workloads_removed = cleanup_campaign_containers()
    compose_removed = compose_down(volumes=volumes)

    if not (
        control_plane_stopped
        and campaign_workloads_removed
        and compose_removed
    ):
        warning("Retrying the final shutdown sweep")
        campaign_workloads_removed = cleanup_campaign_containers()
        if not compose_removed:
            compose_removed = compose_down(volumes=volumes)

    database_finalized = False
    if campaign_workloads_removed and compose_removed:
        database_finalized = finalize_campaigns_for_shutdown()
    else:
        warning(
            "Campaign database state was left unchanged because runtime "
            "teardown did not complete safely"
        )

    if campaign_workloads_removed and compose_removed and database_finalized:
        success("All P-BitM workloads are down")
        return True

    error(
        "Shutdown was incomplete; review the errors above and run `down` again"
    )
    return False


def cmd_status(output_format='table'):
    """Show global status"""
    if output_format == 'json':
        console.print_json(json.dumps(get_status_data()))
        return True

    show_status()
    return True


def cmd_doctor(output_format='table', strict=False):
    """Run read-only preflight checks for the current deployment."""
    from rich.table import Table

    report = DoctorRunner(config).run(strict=strict)
    if output_format == 'json':
        console.print_json(json.dumps(report.to_dict()))
        return report.healthy

    console.print("\n[bold cyan]🩺 P-BitM Doctor[/]\n")
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Check", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Details")
    table.add_column("Recommended action")
    styles = {
        CheckStatus.PASS: "[green]PASS[/]",
        CheckStatus.WARN: "[yellow]WARN[/]",
        CheckStatus.FAIL: "[red]FAIL[/]",
        CheckStatus.SKIP: "[dim]SKIP[/]",
    }
    for check in report.checks:
        table.add_row(
            check.name,
            styles[check.status],
            check.detail,
            check.action or "—",
        )
    console.print(table)

    summary = report.summary
    console.print(
        "\n[dim]"
        f"{summary['pass']} passed, {summary['warn']} warning(s), "
        f"{summary['fail']} failed, {summary['skip']} skipped"
        "[/]"
    )
    console.print()
    if report.healthy:
        success(
            "Environment passed the strict pre-release gate"
            if strict
            else "Environment passed all required checks"
        )
    else:
        error(
            "Pre-release gate failed"
            if strict
            else "Environment needs attention"
        )
    return report.healthy


# =============================================================================
# CAMPAIGN COMMANDS
# =============================================================================

def cmd_campaign_list(output_format='table'):
    """List all campaigns"""
    if output_format == 'json':
        campaigns = get_campaigns()
        console.print_json(json.dumps(campaigns, indent=2))
    else:
        show_campaigns_table()

    return True


def cmd_campaign_status(campaign_id, output_format='table'):
    """Show campaign status"""
    if output_format == 'json':
        campaign = get_campaign_by_id(campaign_id)
        if not campaign:
            error(f"Campaign not found: {campaign_id}")
            return False
        console.print_json(json.dumps(campaign, indent=2))
    else:
        show_campaign_details(campaign_id)

    return True


def cmd_campaign_start(campaign_id):
    """Start campaign container"""
    campaign = get_campaign_by_id(campaign_id)
    if not campaign:
        error(f"Campaign not found: {campaign_id}")
        return False

    return start_campaign_container(campaign.get('id'))


def cmd_campaign_stop(campaign_id):
    """Stop campaign container"""
    campaign = get_campaign_by_id(campaign_id)
    if not campaign:
        error(f"Campaign not found: {campaign_id}")
        return False

    return stop_campaign_container(campaign.get('id'))


def cmd_campaign_logs(campaign_id, follow=False, tail=None):
    """Show campaign logs"""
    campaign = get_campaign_by_id(campaign_id)
    if not campaign:
        error(f"Campaign not found: {campaign_id}")
        return False

    return get_campaign_container_logs(campaign.get('id'), follow=follow, tail=tail)


def cmd_campaign_remove(campaign_id, force=False):
    """Remove campaign and all victims"""
    campaign = get_campaign_by_id(campaign_id)
    if not campaign:
        error(f"Campaign not found: {campaign_id}")
        return False

    if not force and config.get('cli.confirm_destructive', True):
        console.print(f"\n[bold red]⚠️  WARNING:[/]")
        console.print(f"  Campaign: {campaign.get('name')}")
        console.print(f"  This will remove the campaign and all associated victims\n")

        if not Confirm.ask("Continue?"):
            info("Cancelled")
            return False

    console.print(f"\n[cyan]🗑️  Removing campaign: {campaign.get('name')}[/]\n")

    # Stop campaign container
    stop_campaign_container(campaign.get('id'))

    # Stop all victim containers
    victims = get_victims(campaign_id=campaign.get('id'))
    for victim in victims:
        stop_victim_container(campaign.get('id'), victim.get('id'))

    success("✅ Campaign removed")
    return True


def cmd_campaign_dump(campaign_id, output=None, format='json'):
    """Dump campaign data"""
    campaign = get_campaign_by_id(campaign_id)
    if not campaign:
        error(f"Campaign not found: {campaign_id}")
        return False

    if format == 'csv':
        error("CSV format not yet implemented")
        return False

    return dump_campaign_data(campaign.get('id'), output_path=output)


# =============================================================================
# VICTIM COMMANDS
# =============================================================================

def cmd_victim_list(campaign_id, output_format='table'):
    """List victims for campaign"""
    campaign = get_campaign_by_id(campaign_id)
    if not campaign:
        error(f"Campaign not found: {campaign_id}")
        return False

    if output_format == 'json':
        victims = get_victims(campaign_id=campaign.get('id'))
        console.print_json(json.dumps(victims, indent=2))
    else:
        show_victims_table(campaign_id=campaign.get('id'))

    return True


def cmd_victim_status(campaign_id, victim_id, output_format='table'):
    """Show victim status"""
    victim = get_victim_by_id(campaign_id, victim_id)
    if not victim:
        error(f"Victim not found: {victim_id}")
        return False

    if output_format == 'json':
        console.print_json(json.dumps(victim, indent=2))
    else:
        show_victim_details(campaign_id, victim_id)

    return True


def cmd_victim_start(campaign_id, victim_id):
    """Start victim container"""
    victim = get_victim_by_id(campaign_id, victim_id)
    if not victim:
        error(f"Victim not found: {victim_id}")
        return False

    return start_victim_container(campaign_id, victim.get('id'))


def cmd_victim_stop(campaign_id, victim_id):
    """Stop victim container"""
    victim = get_victim_by_id(campaign_id, victim_id)
    if not victim:
        error(f"Victim not found: {victim_id}")
        return False

    return stop_victim_container(campaign_id, victim.get('id'))


def cmd_victim_logs(campaign_id, victim_id, follow=False, tail=None):
    """Show victim logs"""
    victim = get_victim_by_id(campaign_id, victim_id)
    if not victim:
        error(f"Victim not found: {victim_id}")
        return False

    return get_victim_container_logs(campaign_id, victim.get('id'), follow=follow, tail=tail)


# =============================================================================
# ADMIN COMMANDS
# =============================================================================

def cmd_admin_config(edit=False):
    """Show or edit configuration"""
    config_path = Path('config.yaml')

    if edit:
        import subprocess
        import os

        editor = os.environ.get('EDITOR', 'vim')

        try:
            subprocess.run([editor, str(config_path)])
            success("Config edited")
            info("Restart services to apply changes")
            return True
        except Exception as e:
            error(f"Failed to open editor: {e}")
            return False
    else:
        # Show config
        console.print("\n[bold cyan]📝 Current Configuration[/]\n")

        with open(config_path, 'r') as f:
            content = f.read()

        console.print(Panel(
            content,
            title="config.yaml",
            border_style="cyan",
            box=box.ROUNDED
        ))

        console.print(f"\n[dim]Edit with: python3 p-bitm.py admin config --edit[/]\n")
        return True


def cmd_admin_reset_password(username=None):
    from cli.database import reset_admin_password
    """Reset admin password"""
    if not username:
        username = config.get('admin.username', 'admin')

    console.print(f"\n[cyan]🔑 Reset Password for: {username}[/]\n")

    new_password = Prompt.ask("New password", password=True)
    confirm_password = Prompt.ask("Confirm password", password=True)

    if new_password != confirm_password:
        error("Passwords do not match")
        return False

    if len(new_password) < 12:
        error("Password must be at least 12 characters long")
        return False

    return reset_admin_password(username, new_password)


def cmd_admin_users(
    action='list',
    username=None,
    email=None,
    role=None,
    output_format='table',
    force=False,
):
    """Manage local admin/operator accounts."""
    if action == 'list':
        users = get_users()
        if output_format == 'json':
            console.print_json(json.dumps(users, indent=2))
            return True
        if not users:
            info("No users found")
            return True

        table = Table(
            title="Team",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("Username", style="cyan")
        table.add_column("Email")
        table.add_column("Role", style="magenta")
        table.add_column("Status")
        table.add_column("Last Login", style="dim")
        for user in users:
            table.add_row(
                user.get('username', ''),
                user.get('email', ''),
                user.get('role', ''),
                "[green]Active[/]" if user.get('is_active') else "[red]Disabled[/]",
                user.get('last_login') or 'Never',
            )
        console.print(table)
        return True

    if not username:
        error(f"Username is required for '{action}'")
        return False

    if action == 'create':
        if not email:
            error("--email is required when creating a user")
            return False
        selected_role = role or 'operator'
        password = Prompt.ask("Password", password=True)
        confirmation = Prompt.ask("Confirm password", password=True)
        if password != confirmation:
            error("Passwords do not match")
            return False
        return create_local_user(username, email, password, selected_role)

    if action == 'set-role':
        if not role:
            error("--role is required with set-role")
            return False
        return set_local_user_role(username, role)

    if action in {'enable', 'disable'}:
        return set_local_user_active(username, action == 'enable')

    if action == 'delete':
        if not force and not Confirm.ask(
            f"Permanently delete user '{username}' and reassign their campaigns?"
        ):
            info("User deletion cancelled")
            return True
        return delete_local_user(username)

    error(f"Unknown users action: {action}")
    return False


# =============================================================================
# MAINTENANCE
# =============================================================================

def cmd_cleanup(victims=True, campaigns=False):
    """Cleanup containers"""
    console.print("\n[bold cyan]🧹 Cleanup[/]\n")

    if victims:
        cleanup_victim_containers()

    if campaigns:
        if config.get('cli.confirm_destructive', True):
            if not Confirm.ask("⚠️  Remove ALL campaign containers?"):
                info("Skipped campaign cleanup")
            else:
                cleanup_campaign_containers()
        else:
            cleanup_campaign_containers()

    success("\n✅ Cleanup completed")
    return True


def cmd_reset():
    """Complete reset (stop everything, remove all)"""
    if config.get('cli.confirm_destructive', True):
        console.print("\n[bold red]⚠️  WARNING: This will:[/]")
        console.print("  - Stop all services")
        console.print("  - Remove all containers")
        console.print("  - Remove all Docker images")
        console.print("  - Keep database and logs\n")

        if not Confirm.ask("Continue with reset?"):
            info("Cancelled")
            return False

    console.print("\n[bold cyan]🔄 Resetting P-BitM...[/]\n")

    # Stop services
    compose_down(volumes=False)

    # Cleanup containers
    cleanup_victim_containers()
    cleanup_campaign_containers()

    # Remove images
    remove_all_images()

    success("\n✅ Reset completed")
    console.print("\n[dim]Run [bold]python3 p-bitm.py up --build[/] to rebuild and start[/]")

    return True
