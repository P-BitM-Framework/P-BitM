"""Utility functions"""
import os
import platform
import socket
import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich import box

from typing import Union

from cli.config import config
from cli.runtime_env import (
    get_runtime_env_errors,
    is_secure_runtime_secret,
    read_env_file,
)

console = Console()

LOGO = """[bold red]
██████╗       ██████╗ ██╗████████╗███╗   ███╗
██╔══██╗      ██╔══██╗██║╚══██╔══╝████╗ ████║
██████╔╝█████╗██████╔╝██║   ██║   ██╔████╔██║
██╔═══╝ ╚════╝██╔══██╗██║   ██║   ██║╚██╔╝██║
██║           ██████╔╝██║   ██║   ██║ ╚═╝ ██║
╚═╝           ╚═════╝ ╚═╝   ╚═╝   ╚═╝     ╚═╝[/]
"""

def show_banner():
    """Display startup banner"""
    console.print()

    # Logo centrato
    console.print(Align.center(LOGO))

    panel_text = Text()
    panel_text.append("🎣 Persistent Browser-in-the-Middle Framework 🎣\n", style="bold cyan")
    panel_text.append("Advanced Spear-Phishing Infrastructure Manager\n\n", style="dim")
    panel_text.append("Version: ", style="yellow")
    panel_text.append("0.1.0", style="white")
    panel_text.append("  |  ", style="dim")
    panel_text.append("Author: ", style="yellow")
    panel_text.append("@GiacoLenzo2109 @MrSaighnal", style="white")
    panel_text.append("  |  ", style="dim")
    panel_text.append("License: ", style="yellow")
    panel_text.append("GPLv3-only", style="white")

    # Centra il testo
    panel_text.justify = "center"

    # Info panel
    info = Panel(
        panel_text,
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(Align.center(info))
    console.print()

def should_show_banner(command_name=None, is_help=False):
    """
    Determine if banner should be shown based on config

    Args:
        command_name: Name of the command being executed (e.g., 'up', 'status')
        is_help: True if showing help screen (no command or -h flag)

    Returns:
        bool: True if banner should be shown
    """
    # Check if banner globally disabled
    if not config.get('cli.banner_enabled', True):
        return False

    # Help screen
    if is_help:
        return config.get('cli.banner_on_help', True)

    # Check command against whitelist
    banner_commands = config.get('cli.banner_commands', ['up', 'setup'])

    if banner_commands in ['all', '*']:
        return True

    if command_name in banner_commands:
        return True

    return False


def success(message: str):
    """Print success message"""
    console.print(f"[bold green]✓[/] {message}")


def error(message: str):
    """Print error message"""
    console.print(f"[bold red]✗[/] {message}")


def warning(message: str):
    """Print warning message"""
    console.print(f"[bold yellow]⚠[/]  {message}")


def info(message: str):
    """Print info message"""
    console.print(f"[cyan]ℹ[/]  {message}")


def get_arch() -> str:
    """
    Detect CPU architecture

    Returns:
        'amd64' or 'arm64'
    """
    machine = platform.machine().lower()

    if machine in ['x86_64', 'amd64']:
        return 'amd64'
    elif machine in ['aarch64', 'arm64']:
        return 'arm64'
    else:
        warning(f"Unknown architecture: {machine}, defaulting to amd64")
        return 'amd64'


# Not currently called anywhere; kept alongside get_arch() as a ready helper
# for a future host-OS-specific check (e.g. warning on unsupported hosts).
def get_os_type() -> str:
    """
    Detect OS type

    Returns:
        'darwin' (macOS) or 'linux'
    """
    return platform.system().lower()


def get_local_ip() -> str:
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def generate_ssl_certs(ip: str, cert_path: str, key_path: str) -> bool:
    """Generate self-signed SSL certificates"""
    from cli.config import config

    cert_dir = Path(cert_path).parent
    cert_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "openssl", "req", "-new", "-x509",
        "-days", str(config.get('ssl.validity_days', 365)),
        "-nodes",
        "-out", cert_path,
        "-keyout", key_path,
        "-subj", f"/C={config.get('ssl.country', 'IT')}"
                 f"/ST={config.get('ssl.state', 'Lombardy')}"
                 f"/L={config.get('ssl.city', 'Milan')}"
                 f"/O={config.get('ssl.organization', 'P-BitM')}"
                 f"/CN={ip}"
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        error(f"Failed to generate SSL certificates: {e}")
        return False


def copy_certs_to_containers():
    """Copy certificates to container build contexts"""
    from cli.config import config
    import shutil

    certs_dir = Path(config.get('paths.certs_dir', './certs'))

    if not certs_dir.exists():
        return

    # Copy to frontend
    frontend_certs = Path('./server/frontend/certs')
    frontend_certs.mkdir(parents=True, exist_ok=True)
    frontend_certs.chmod(0o755)

    for file_name, mode in (("cert.pem", 0o644), ("key.pem", 0o600)):
        source = certs_dir / file_name
        destination = frontend_certs / file_name
        if not source.is_file() or source.is_symlink():
            raise RuntimeError(f"Invalid TLS source file: {source}")
        if destination.is_symlink() or (
            destination.exists() and not destination.is_file()
        ):
            raise RuntimeError(f"Invalid TLS build-context path: {destination}")
        shutil.copyfile(source, destination)
        destination.chmod(mode)


def ensure_storage_directories() -> tuple[Path, Path]:
    """Reconcile host storage paths required by every application start."""
    project_root = Path(__file__).parent.parent.resolve()
    configured_paths = (
        config.get("paths.storage_dir", "./storage"),
        config.get("paths.campaigns_dir", "./storage/campaigns"),
    )
    resolved_paths = []
    for configured_path in configured_paths:
        path = Path(configured_path)
        if not path.is_absolute():
            path = project_root / path
        path = path.resolve()
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(0o755)
        resolved_paths.append(path)
    return tuple(resolved_paths)


def generate_env_file():
    """Generate runtime config while preserving valid existing credentials."""
    from pathlib import Path
    import secrets
    from cli.database import generate_secure_password

    # Get project root and reconcile storage paths on every setup/up. Runtime
    # subdirectories may legitimately be absent from a fresh checkout.
    project_root = Path(__file__).parent.parent.resolve()
    storage_path, _ = ensure_storage_directories()
    env_file = project_root / "server" / ".env"

    # Preserve credentials generated by an earlier setup. Re-running setup must
    # not invalidate sessions or break the internal API shared by containers.
    existing_env = read_env_file(env_file)

    existing_admin_password = existing_env.get('ADMIN_PASSWORD', '')
    existing_internal_key = existing_env.get('INTERNAL_API_KEY', '')
    existing_data_encryption_key = existing_env.get('DATA_ENCRYPTION_KEY', '')

    password_generated = not is_secure_runtime_secret(existing_admin_password, 16)
    admin_password = (
        existing_admin_password
        if not password_generated
        else generate_secure_password(32)
    )
    internal_api_key = (
        existing_internal_key
        if is_secure_runtime_secret(existing_internal_key, 32)
        else secrets.token_urlsafe(32)
    )
    data_encryption_key = (
        existing_data_encryption_key
        if is_secure_runtime_secret(existing_data_encryption_key, 32)
        else secrets.token_urlsafe(32)
    )

    # Get other config values
    admin_username = config.get('admin.username', 'admin')
    admin_email = config.get('admin.email', 'admin@bitm.local')
    # log_level = config.get('logging.level', 'INFO')

    environment = config.get('app.environment', 'production')
    if environment not in {'development', 'production'}:
        raise ValueError("app.environment must be development or production")
    for field_name, field_value in (
        ('admin.username', admin_username),
        ('admin.email', admin_email),
    ):
        if not isinstance(field_value, str) or not field_value.strip():
            raise ValueError(f"{field_name} must not be empty")
        if any(character in field_value for character in "\r\n="):
            raise ValueError(f"{field_name} contains invalid characters")

    # Write .env file
    env_content = f"""# P-BitM Environment Configuration
# Auto-generated by CLI

ENVIRONMENT={environment}

# Storage paths (HOST)
HOST_STORAGE_PATH={storage_path}

# Storage paths (container)
STORAGE_PATH=/storage
DB_PATH=/storage/p-bitm.db

# Admin credentials
ADMIN_USERNAME={admin_username}
ADMIN_PASSWORD={admin_password}
ADMIN_EMAIL={admin_email}
ADMIN_SESSION_TTL_HOURS={config.get('admin.session_ttl_hours', 12)}
ADMIN_MAX_SESSIONS_PER_USER={config.get('admin.max_sessions_per_user', 5)}

# Security
INTERNAL_API_KEY={internal_api_key}
DATA_ENCRYPTION_KEY={data_encryption_key}

# Public session admission
SESSION_TOKEN_TTL_SECONDS={config.get('sessions.token_ttl_seconds', 300)}
WS_HANDSHAKE_TIMEOUT_SECONDS={config.get('sessions.handshake_timeout_seconds', 10)}
WS_SESSION_STARTUP_TIMEOUT_SECONDS={config.get('sessions.startup_timeout_seconds', 45)}
MAX_ACTIVE_SESSIONS={config.get('sessions.max_active', 20)}
WS_RATE_LIMIT_WINDOW_SECONDS={config.get('sessions.rate_limit_window_seconds', 60)}
WS_RATE_LIMIT_MAX_ATTEMPTS={config.get('sessions.max_attempts_per_client', 10)}
WS_GLOBAL_RATE_LIMIT_MAX_ATTEMPTS={config.get('sessions.max_attempts_global', 200)}

# Docker
DOCKER_SOCKET=/var/run/docker.sock
DOCKER_NETWORK=server_bitm-network
CAMPAIGN_IMAGE=p-bitm:latest
EGRESS_IMAGE=p-bitm-egress:latest

# Network
IP=127.0.0.1

"""

    env_file.parent.mkdir(parents=True, exist_ok=True)
    with open(env_file, 'w') as f:
        f.write(env_content)
    env_file.chmod(0o600)

    return {
        'env_file': env_file,
        'admin_username': admin_username,
        'admin_password': admin_password,
        'password_generated': password_generated,
        'storage_path': storage_path
    }


def ensure_dns_challenge(force: bool = False) -> bool:
    """Provision provider-specific DNS credentials and Traefik runtime files."""
    import re
    import yaml

    project_root = Path(__file__).parent.parent.resolve()
    dns_config = config.get('ssl.dns_challenge', {})
    provider = str(dns_config.get('provider', '')).strip()
    credentials = dns_config.get('credentials', [])
    public_environment = dns_config.get('environment', {})

    if not provider or not re.fullmatch(r'[A-Za-z0-9_-]+', provider):
        error("ssl.dns_challenge.provider is missing or invalid in config.yaml")
        return False
    if not isinstance(credentials, list) or not isinstance(public_environment, dict):
        error("DNS credentials must be a list and environment must be a mapping")
        return False

    def project_path(config_key, default):
        path = Path(config.get(config_key, default))
        return path if path.is_absolute() else project_root / path

    secrets_dir = project_path('paths.dns_secrets_dir', './server/.secrets/dns')
    dns_env_path = project_path('paths.traefik_dns_env_file', './server/.traefik-dns.env')
    template_path = project_path(
        'paths.traefik_prod_template',
        './server/traefik/traefik.prod.template.yml'
    )
    runtime_path = project_path(
        'paths.traefik_prod_runtime',
        './server/traefik/traefik.prod.runtime.yml'
    )

    secrets_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    secrets_dir.chmod(0o700)
    legacy_env = read_env_file(project_root / 'server' / '.env')
    legacy_duckdns_path = project_root / 'server' / '.secrets' / 'duckdns_token'

    for variable in credentials:
        variable = str(variable).strip()
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', variable):
            error(f"Invalid DNS credential variable: {variable}")
            return False

        secret_path = secrets_dir / variable
        if not force and secret_path.exists() and secret_path.read_text().strip():
            secret_path.chmod(0o600)
            continue

        # Migrate the original DuckDNS-specific file without exposing its value.
        if (
            not force
            and variable == 'DUCKDNS_TOKEN'
            and legacy_duckdns_path.exists()
            and legacy_duckdns_path.read_text().strip()
        ):
            legacy_duckdns_path.replace(secret_path)
            secret_path.chmod(0o600)
            info(f"Migrated {variable} to {secret_path.relative_to(project_root)}")
            continue

        value = os.environ.get(variable, '').strip()
        if not value and not force:
            value = legacy_env.get(variable, '').strip()

        if not value:
            if not sys.stdin.isatty():
                error(
                    f"{variable} is missing. Set it for this setup run or "
                    "run setup interactively."
                )
                return False

            from rich.prompt import Prompt
            value = Prompt.ask(
                f"{provider} credential {variable} (stored locally, input hidden)",
                password=True
            ).strip()

        if not value:
            error(f"{variable} cannot be empty")
            return False

        secret_path.write_text(f"{value}\n")
        secret_path.chmod(0o600)

    env_lines = [
        "# Auto-generated by P-BitM CLI; contains paths, not secret values."
    ]
    for variable in credentials:
        variable = str(variable).strip()
        env_lines.append(f"{variable}_FILE=/run/secrets/dns/{variable}")

    for variable, value in public_environment.items():
        variable = str(variable).strip()
        value = str(value)
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', variable) or '\n' in value:
            error(f"Invalid DNS environment entry: {variable}")
            return False
        env_lines.append(f"{variable}={value}")

    dns_env_path.parent.mkdir(parents=True, exist_ok=True)
    dns_env_path.write_text('\n'.join(env_lines) + '\n')
    dns_env_path.chmod(0o600)

    if not template_path.exists():
        error(f"Traefik production template not found: {template_path}")
        return False

    runtime_config = yaml.safe_load(template_path.read_text()) or {}
    try:
        acme = runtime_config['certificatesResolvers']['letsencrypt']['acme']
        acme['email'] = config.get('ssl.acme_email', 'admin@example.com')
        acme['dnsChallenge']['provider'] = provider
    except (KeyError, TypeError):
        error(f"Invalid Traefik production template: {template_path}")
        return False

    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(yaml.safe_dump(runtime_config, sort_keys=False))
    runtime_path.chmod(0o644)

    success(
        f"DNS challenge configured for {provider} "
        f"with {len(credentials)} credential file(s)"
    )
    return True

def update_env_file(ip: str):
    """Update .env file with current IP"""
    from cli.config import config

    project_root = Path(__file__).parent.parent.resolve()
    env_file = Path(config.get('paths.env_file', './server/.env'))
    if not env_file.is_absolute():
        env_file = project_root / env_file

    if not env_file.exists():
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text(f"IP={ip}\n")
        env_file.chmod(0o600)
        info(f"Created .env with IP={ip}")
        return

    content = env_file.read_text()
    lines = content.split('\n')
    updated = False

    for i, line in enumerate(lines):
        if line.startswith('IP='):
            lines[i] = f'IP={ip}'
            updated = True
            break

    if not updated:
        lines.append(f'IP={ip}')

    env_file.write_text('\n'.join(lines))
    env_file.chmod(0o600)
    info(f"Updated .env with IP={ip}")

def show_admin_credentials(username, password):
    """Display admin credentials in a nice panel"""
    from rich.table import Table

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column(style="bold white")

    table.add_row("Username:", username)
    table.add_row("Password:", password)

    panel = Panel(
        table,
        title="[bold yellow]🔐 Admin Credentials[/]",
        subtitle="[dim]Save these credentials securely![/]",
        border_style="yellow",
        padding=(1, 2)
    )

    console.print()
    console.print(panel)
    console.print()

def run_command(
    cmd: list,
    capture: bool = False,
    quiet: bool = False
) -> Union[str, bool]:
    """Execute shell command with output control"""
    try:
        if capture:
            result = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return result.stdout.strip() if result.stdout else ""
        else:
            if quiet:
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            else:
                subprocess.run(cmd, check=True)
            return True

    except subprocess.CalledProcessError as e:
        console.print(f"[red]✗ Command failed: {' '.join(cmd)}[/]")
        details = (e.stderr or '').strip() if isinstance(e.stderr, str) else ''
        if details:
            console.print(f"[dim red]{details}[/]")
        return "" if capture else False




def check_docker_image(image_name: str) -> bool:
    """Check if Docker image exists"""
    try:
        result = subprocess.run(
            ["docker", "images", "-q", image_name],
            capture_output=True,
            text=True,
            check=True
        )
        return bool(result.stdout.strip())
    except:
        return False


def build_docker_image(image_name: str, dockerfile: str, context: str) -> bool:
    """
    Build Docker image

    Args:
        image_name: Tag for the image (e.g., 'bitm-vnc:latest')
        dockerfile: Path to Dockerfile (relative to project root)
        context: Build context directory

    Returns:
        True if successful
    """
    console.print(f"\n[cyan]🔨 Building Docker image: {image_name}...[/]")

    cmd = [
        "docker", "build",
        "-t", image_name,
        "-f", dockerfile,
        context
    ]

    try:
        if not run_command(cmd, quiet=False):
            error(f"Failed to build {image_name}")
            return False
        success(f"Built {image_name}")
        return True
    except subprocess.CalledProcessError:
        error(f"Failed to build {image_name}")
        return False


def build_all_images(force: bool = False) -> bool:
    """
    Build all required Docker images

    Builds:
    - bitm-vnc:latest
    - bitm-selkies:latest (multi-arch by default)
    - p-bitm:latest
    """
    from cli.config import config

    arch = get_arch()
    console.print(f"\n[cyan]📦 Detected architecture: {arch}[/]")

    all_success = True

    # Get images from config
    images_config = config.get('docker.images', {})

    for image_key, image_data in images_config.items():
        if not image_data.get('enabled', True):
            info(f"Skipping disabled image: {image_key}")
            continue

        image_name = image_data.get('name')
        context = image_data.get('context')

        # Check if image already exists
        if not force and check_docker_image(image_name):
            info(f"Image {image_name} already exists")
            continue

        # Prefer architecture-specific Dockerfiles when both are configured;
        # otherwise use the common multi-arch Dockerfile.
        if 'dockerfile_amd64' in image_data and 'dockerfile_arm64' in image_data:
            if arch == 'amd64':
                dockerfile = image_data.get('dockerfile_amd64')
            else:
                dockerfile = image_data.get('dockerfile_arm64')
            console.print(f"\n[cyan]Using {dockerfile} for {arch}[/]")
        else:
            dockerfile = image_data.get('dockerfile')

        # Build image
        if not build_docker_image(image_name, dockerfile, context):
            all_success = False

    return all_success


def check_compose_images_exist() -> bool:
    """
    Check if all compose-built images exist

    Returns:
        True if all images exist, False if at least one is missing
    """
    from cli.config import config

    compose_images = config.get('docker.compose_images', [])

    for image in compose_images:
        if not check_docker_image(image):
            return False

    return True


def get_docker_compose_command() -> list:
    """
    Get appropriate docker-compose command

    Returns:
        ['docker', 'compose'] or ['docker-compose']
    """
    # Try docker compose (plugin) first
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            check=True
        )
        return ["docker", "compose"]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Try docker-compose (standalone)
    try:
        result = subprocess.run(
            ["docker-compose", "--version"],
            capture_output=True,
            check=True
        )
        return ["docker-compose"]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    error("Docker Compose not found! Install docker compose plugin or docker-compose")
    return None


def cleanup_victim_containers():
    """
    Cleanup all app-owned victim containers.
    """
    console.print("[cyan]Cleaning up victim containers...[/]")

    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "-aq",
                "--filter",
                "label=bitm.role=victim",
            ],
            capture_output=True,
            text=True,
            check=True
        )

        victim_ids = result.stdout.strip().split('\n')
        victim_ids = [cid for cid in victim_ids if cid]

        if not victim_ids:
            info("No victim containers found")
            return

        for cid in victim_ids:
            subprocess.run(
                ["docker", "rm", "-f", cid],
                capture_output=True,
                check=True,
            )

        success(f"Cleaned up {len(victim_ids)} victim containers")

    except subprocess.CalledProcessError as e:
        warning(f"Failed to cleanup some victim containers: {e}")


def cleanup_campaign_containers():
    """
    Cleanup all app-owned campaign containers and isolated networks.
    """
    console.print("[cyan]Cleaning up campaign workloads...[/]")

    failures = []
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "-aq",
                "--filter",
                "label=bitm.campaign.id",
            ],
            capture_output=True,
            text=True,
            check=True
        )

        container_ids = [
            cid for cid in result.stdout.strip().splitlines() if cid
        ]

        if container_ids:
            removed_count = 0
            for cid in container_ids:
                try:
                    subprocess.run(
                        ["docker", "rm", "-f", cid],
                        capture_output=True,
                        check=True,
                    )
                    removed_count += 1
                except (subprocess.CalledProcessError, OSError) as exc:
                    failures.append(f"container {cid}: {exc}")
            if removed_count:
                success(f"Cleaned up {removed_count} campaign workloads")
        else:
            info("No campaign workloads found")
    except (subprocess.CalledProcessError, OSError) as exc:
        failures.append(f"campaign workload discovery: {exc}")

    network_ids = set()
    for role in ("campaign-private", "campaign-egress"):
        try:
            network_result = subprocess.run(
                [
                    "docker",
                    "network",
                    "ls",
                    "-q",
                    "--filter",
                    f"label=bitm.role={role}",
                    "--filter",
                    "label=bitm.campaign.id",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            network_ids.update(
                network_id
                for network_id in network_result.stdout.strip().splitlines()
                if network_id
            )
        except (subprocess.CalledProcessError, OSError) as exc:
            failures.append(f"{role} network discovery: {exc}")

    removed_networks = 0
    for network_id in sorted(network_ids):
        try:
            subprocess.run(
                ["docker", "network", "rm", network_id],
                capture_output=True,
                check=True,
            )
            removed_networks += 1
        except (subprocess.CalledProcessError, OSError) as exc:
            failures.append(f"network {network_id}: {exc}")

    if removed_networks:
        success(f"Cleaned up {removed_networks} campaign networks")
    elif not network_ids:
        info("No campaign networks found")

    if failures:
        for failure in failures:
            warning(f"Failed to clean up {failure}")
        return False

    return True


def remove_all_images():
    """Remove all P-BitM Docker images"""
    from cli.config import config

    console.print("[cyan]Removing Docker images...[/]")

    # Get all custom images
    images_to_remove = []

    images_config = config.get('docker.images', {})
    for image_data in images_config.values():
        images_to_remove.append(image_data.get('name'))

    # Add compose images
    compose_images = config.get('docker.compose_images', [])
    images_to_remove.extend(compose_images)

    for image in images_to_remove:
        if check_docker_image(image):
            try:
                subprocess.run(
                    ["docker", "rmi", image],
                    capture_output=True,
                    check=True
                )
                info(f"Removed {image}")
            except subprocess.CalledProcessError:
                warning(f"Failed to remove {image}")


def install_completion():
    """Install shell completion"""
    console.print("\n[bold cyan]🔧 Installing Shell Completion[/]\n")

    try:
        import argcomplete
    except ImportError:
        error("argcomplete not installed. Run: pip install argcomplete")
        console.print("\n[dim]Or install all dependencies:[/]")
        console.print("[yellow]pip install -r requirements.txt[/]\n")
        return

    shell = os.environ.get('SHELL', '').split('/')[-1]
    script_path = Path(__file__).parent.parent / 'pbitm.py'
    script_name = 'pbitm.py'

    if shell == 'bash':
        completion_line = f'eval "$(register-python-argcomplete {script_name})"'
        rc_file = Path.home() / '.bashrc'

        console.print(f"[cyan]Detected shell:[/] bash")
        console.print(f"[cyan]Add this line to {rc_file}:[/]\n")
        console.print(f"[yellow]{completion_line}[/]\n")

        info(f"Or run: echo '{completion_line}' >> {rc_file}")
        info("Then: source ~/.bashrc")

        console.print("\n[dim]Alternative (global activation for all Python argcomplete scripts):[/]")
        console.print("[yellow]activate-global-python-argcomplete --user[/]")
        console.print("[yellow]# Then add to ~/.bashrc: eval \"$(register-python-argcomplete pbitm.py)\"[/]")

    elif shell == 'zsh':
        completion_line = f'eval "$(register-python-argcomplete {script_name})"'
        rc_file = Path.home() / '.zshrc'

        console.print(f"[cyan]Detected shell:[/] zsh")
        console.print(f"[cyan]Add these lines to {rc_file}:[/]\n")

        console.print("[yellow]# Enable bash completion compatibility[/]")
        console.print("[yellow]autoload -U bashcompinit[/]")
        console.print("[yellow]bashcompinit[/]\n")
        console.print(f"[yellow]{completion_line}[/]\n")

        info(f"Then: source ~/.zshrc")

    else:
        warning(f"Unknown shell: {shell}")
        console.print("\n[dim]For manual setup, see:[/]")
        console.print("[blue]https://github.com/kislyuk/argcomplete#synopsis[/]")

    success("\n✅ Instructions displayed")
    console.print("\n[bold cyan]After setup, test with:[/]")
    console.print(f"[yellow]python3 p-bitm.py <TAB><TAB>[/]")
    console.print(f"[yellow]python3 p-bitm.py campaign <TAB><TAB>[/]")
    console.print(f"[yellow]python3 p-bitm.py campaign abc123 <TAB><TAB>[/]\n")
