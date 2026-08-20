"""Docker operations using the Docker Compose and Buildx plugins."""
import subprocess
import docker
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich import box

from cli.config import config
from cli.utils import (
    success, error, warning, info, run_command,
    get_docker_compose_command, check_docker_image,
    build_all_images, copy_certs_to_containers,
    check_compose_images_exist,
    docker_buildkit_is_disabled, docker_engine_is_supported,
    get_docker_buildx_version,
    get_docker_compose_version, MIN_DOCKER_ENGINE_VERSION,
)

console = Console()

# Docker is initialized lazily so read-only commands such as --help and
# configuration inspection do not require access to the daemon.
docker_client = None


def get_docker_client():
    global docker_client
    if docker_client is None:
        try:
            docker_client = docker.from_env()
        except Exception:
            return None
    return docker_client

ENVIRONMENT = config.get('app.environment', 'production')
if ENVIRONMENT == 'development':
    COMPOSE_FILE = Path(config.get('paths.docker_compose_dev', './server/docker-compose-dev.yml'))
else:
    COMPOSE_FILE = Path(config.get('paths.docker_compose', './server/docker-compose.yml'))

def check_docker():
    """Check Docker availability"""
    client = get_docker_client()
    if not client:
        error("Docker not installed or not running")
        return False

    try:
        version = client.version()
        engine_version = version.get('Version', 'unknown')
    except Exception:
        error("Docker daemon not running")
        return False

    if not docker_engine_is_supported(engine_version):
        minimum = ".".join(str(part) for part in MIN_DOCKER_ENGINE_VERSION)
        error(
            f"Docker Engine {minimum} or newer is required "
            f"(found {engine_version})"
        )
        return False
    success(f"Docker Engine {engine_version} available")

    if docker_buildkit_is_disabled():
        error(
            "BuildKit is disabled by DOCKER_BUILDKIT=0. Unset this "
            "environment variable and retry."
        )
        return False

    buildx_version = get_docker_buildx_version()
    if buildx_version is None:
        error(
            "Docker Buildx plugin is required. Install the plugin package "
            "provided by your Docker distribution and verify it with "
            "`docker buildx version`."
        )
        return False
    success(f"Docker Buildx available: {buildx_version}")

    compose_version = get_docker_compose_version()
    if compose_version is None:
        error(
            "Docker Compose plugin is required. Install the Compose v2 "
            "plugin package provided by your Docker distribution and "
            "verify it with `docker compose version`; standalone "
            "`docker-compose` is not supported."
        )
        return False
    success(f"Docker Compose available: {compose_version}")
    return True


def compose_up(build=False, detach=True):
    """Start services with the Docker Compose plugin."""
    compose_cmd = get_docker_compose_command()
    if not compose_cmd:
        return False

    console.print("\n[cyan]🚀 Starting services...[/]")

    # Copy certificates into the frontend build context with deterministic
    # host-side modes. The Dockerfile assigns its private copy to nginx.
    try:
        copy_certs_to_containers()
    except (OSError, RuntimeError) as exc:
        error(f"Failed to prepare frontend TLS files: {exc}")
        return False

    # Build custom images first (bitm-vnc, bitm-selkies, p-bitm)
    if build:
        console.print("[cyan]Building custom images...[/]")
        if not build_all_images(force=True):
            error("One or more custom images failed to build")
            return False
    else:
        # Check if custom images exist, build if missing
        images_config = config.get('docker.images', {})
        missing_images = []

        for image_data in images_config.values():
            if image_data.get('enabled', True):
                image_name = image_data.get('name')
                if not check_docker_image(image_name):
                    missing_images.append(image_name)

        if missing_images:
            console.print(f"[cyan]Missing images: {', '.join(missing_images)}[/]")
            console.print("[cyan]Building...[/]")
            if not build_all_images():
                error("One or more required images failed to build")
                return False

    # Check if Compose images (frontend/backend) exist
    need_compose_build = not check_compose_images_exist()

    if need_compose_build:
        info("Frontend/Backend images missing, will build via Docker Compose")

    # Build Docker Compose command
    cmd = compose_cmd + ["-f", str(COMPOSE_FILE), "up"]

    if detach:
        cmd.append("-d")

    # Add --build only if needed
    if build or need_compose_build:
        cmd.append("--build")

    cmd.append("--remove-orphans")

    with console.status("[bold cyan]Starting containers...", spinner="dots"):
        if run_command(cmd, quiet=True):
            success("Services started successfully")

            # Show dashboard URL
            dashboard_url = config.get('app.dashboard_url', 'https://127.0.0.1:8443/')
            console.print(f"\n[bold magenta]🎯 Dashboard URL:[/] [bold white]{dashboard_url}[/]")

            return True
        else:
            error("Failed to start services")
            return False


def compose_down(volumes=False):
    """Stop services"""
    compose_cmd = get_docker_compose_command()
    if not compose_cmd:
        return False

    console.print("\n[cyan]🛑 Stopping services...[/]")

    cmd = compose_cmd + ["-f", str(COMPOSE_FILE), "down"]

    if volumes:
        cmd.append("--volumes")
        warning("This will delete all volumes and data!")

    with console.status("[bold cyan]Stopping containers...", spinner="dots"):
        if run_command(cmd):
            success("Services stopped")
            return True
        else:
            error("Failed to stop services")
            return False


def compose_stop():
    """Stop the control plane while keeping its networks available for teardown."""
    compose_cmd = get_docker_compose_command()
    if not compose_cmd:
        return False

    cmd = compose_cmd + ["-f", str(COMPOSE_FILE), "stop"]
    with console.status(
        "[bold cyan]Stopping the control plane...",
        spinner="dots",
    ):
        if run_command(cmd):
            return True

    error("Failed to stop the control plane")
    return False


def compose_ps():
    """List compose services with status"""
    compose_cmd = get_docker_compose_command()
    if not compose_cmd:
        return []

    cmd = compose_cmd + ["-f", str(COMPOSE_FILE), "ps", "--format", "json"]

    result = run_command(cmd, capture=True, quiet=True)
    if result:
        import json
        try:
            # Handle both single JSON object and JSON lines
            if result.startswith('['):
                return json.loads(result)
            else:
                # JSON lines format
                services = []
                for line in result.strip().split('\n'):
                    if line:
                        services.append(json.loads(line))
                return services
        except json.JSONDecodeError:
            return []
    return []


def get_status_data():
    """Return the global status without Rich formatting for JSON clients."""
    pattern = config.get('containers.campaign_pattern', 'p-bitm-')
    campaign_containers = []
    try:
        result = subprocess.run(
            [
                "docker", "ps", "-a", "--filter", f"name={pattern}",
                "--format", "{{json .}}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        import json
        campaign_containers = [
            json.loads(line)
            for line in result.stdout.splitlines()
            if line.strip()
        ]
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        campaign_containers = []

    image_names = [
        image_data.get('name')
        for image_data in (config.get('docker.images', {}) or {}).values()
        if image_data.get('enabled', True) and image_data.get('name')
    ]
    image_names.extend(config.get('docker.compose_images', []) or [])
    images = []
    for image_name in image_names:
        exists = check_docker_image(image_name)
        size = None
        if exists:
            try:
                result = subprocess.run(
                    [
                        "docker", "images", image_name,
                        "--format", "{{.Size}}",
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                size = result.stdout.strip().splitlines()[0] or None
            except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
                size = None
        images.append({"name": image_name, "available": exists, "size": size})

    return {
        "services": compose_ps(),
        "campaign_containers": campaign_containers,
        "images": images,
    }


def show_status():
    """Show detailed status of all services and containers"""
    console.print("\n[bold cyan]📊 P-BitM Status[/]\n")

    # Main services status
    services = compose_ps()

    if services:
        table = Table(
            title="Main Services",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )

        table.add_column("Service", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Ports", style="yellow")

        for svc in services:
            name = svc.get('Name', svc.get('Service', 'unknown'))
            state = svc.get('State', 'unknown')

            # Color code status
            if state == 'running':
                status = f"[green]●[/] {state}"
            else:
                status = f"[red]●[/] {state}"

            ports = svc.get('Publishers', [])
            if isinstance(ports, list) and ports:
                port_str = ", ".join([f"{p.get('PublishedPort', '?')}->{p.get('TargetPort', '?')}" for p in ports])
            else:
                port_str = "-"

            table.add_row(name, status, port_str)

        console.print(table)
    else:
        warning("No services running")
        console.print(f"\n[dim]Start services with: [bold]python3 p-bitm.py up[/][/]\n")

    # Campaign containers
    console.print()
    list_campaign_containers()

    # Images status
    console.print()
    show_images_status()


def list_campaign_containers():
    """List all campaign containers"""
    pattern = config.get('containers.campaign_pattern', 'p-bitm-')

    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={pattern}", "--format", "{{.ID}}|{{.Names}}|{{.Status}}|{{.CreatedAt}}"],
            capture_output=True,
            text=True,
            check=True
        )

        lines = [l for l in result.stdout.strip().split('\n') if l]

        if not lines:
            info("No campaign containers found")
            return

        table = Table(
            title="Campaign Containers",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )

        table.add_column("Container ID", style="cyan")
        table.add_column("Name", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Created", style="dim")

        for line in lines:
            parts = line.split('|')
            if len(parts) >= 4:
                cid, name, status, created = parts[0], parts[1], parts[2], parts[3]

                # Color code status
                if 'Up' in status:
                    status_colored = f"[green]{status}[/]"
                elif 'Exited' in status:
                    status_colored = f"[red]{status}[/]"
                else:
                    status_colored = status

                table.add_row(cid[:12], name, status_colored, created)

        console.print(table)

    except subprocess.CalledProcessError:
        warning("Failed to list campaign containers")


def show_images_status():
    """Show status of Docker images"""
    table = Table(
        title="Docker Images",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )

    table.add_column("Image", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Size", style="yellow")

    # Check custom images
    images_config = config.get('docker.images', {})
    for image_data in images_config.values():
        image_name = image_data.get('name')

        if check_docker_image(image_name):
            # Get size
            try:
                result = subprocess.run(
                    ["docker", "images", image_name, "--format", "{{.Size}}"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                size = result.stdout.strip().split('\n')[0] if result.stdout else "-"
            except:
                size = "-"

            table.add_row(image_name, "[green]✓ Built[/]", size)
        else:
            table.add_row(image_name, "[red]✗ Missing[/]", "-")

    # Check compose images
    compose_images = config.get('docker.compose_images', [])
    for image_name in compose_images:
        if check_docker_image(image_name):
            try:
                result = subprocess.run(
                    ["docker", "images", image_name, "--format", "{{.Size}}"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                size = result.stdout.strip().split('\n')[0] if result.stdout else "-"
            except:
                size = "-"

            table.add_row(image_name, "[green]✓ Built[/]", size)
        else:
            table.add_row(image_name, "[red]✗ Missing[/]", "-")

    console.print(table)


# =============================================================================
# CAMPAIGN CONTAINER OPERATIONS
# =============================================================================

def get_campaign_container_name(campaign_id: str) -> str:
    """Get container name for campaign"""
    pattern = config.get('containers.campaign_pattern', 'p-bitm-')
    return f"{pattern}{campaign_id[:8]}"


def get_victim_container_name(campaign_id: str, victim_id: str) -> str:
    """Get container name for victim"""
    pattern = config.get('containers.victim_pattern', 'p-bitm-')
    return f"{pattern}{campaign_id}-{victim_id}"


def find_container_by_name_pattern(pattern: str):
    """Find container by name pattern"""
    try:
        client = get_docker_client()
        if not client:
            error("Docker not installed or not running")
            return None
        containers = client.containers.list(all=True, filters={"name": pattern})
        if containers:
            return containers[0]
        return None
    except Exception as e:
        error(f"Failed to find container: {e}")
        return None


def start_campaign_container(campaign_id: str) -> bool:
    """Start campaign container"""
    container_name = get_campaign_container_name(campaign_id)
    console.print(f"\n[cyan]▶️  Starting campaign container: {container_name}[/]")

    container = find_container_by_name_pattern(container_name)

    if not container:
        error(f"Container not found: {container_name}")
        info("Campaign containers are created by the backend when a campaign is started via the dashboard")
        return False

    try:
        if container.status == 'running':
            info(f"Container already running: {container_name}")
            return True

        container.start()
        success(f"Started container: {container_name}")
        return True

    except Exception as e:
        error(f"Failed to start container: {e}")
        return False


def stop_campaign_container(campaign_id: str) -> bool:
    """Stop campaign container"""
    container_name = get_campaign_container_name(campaign_id)
    console.print(f"\n[cyan]⏸️  Stopping campaign container: {container_name}[/]")

    container = find_container_by_name_pattern(container_name)

    if not container:
        warning(f"Container not found: {container_name}")
        return True  # Already stopped/removed

    try:
        if container.status != 'running':
            info(f"Container already stopped: {container_name}")
            return True

        container.stop(timeout=10)
        success(f"Stopped container: {container_name}")
        return True

    except Exception as e:
        error(f"Failed to stop container: {e}")
        return False


def get_campaign_container_logs(campaign_id: str, follow=False, tail=None) -> bool:
    """Show campaign container logs"""
    container_name = get_campaign_container_name(campaign_id)

    container = find_container_by_name_pattern(container_name)

    if not container:
        error(f"Container not found: {container_name}")
        return False

    try:
        if follow:
            console.print(f"\n[cyan]📜 Following logs for: {container_name}[/]")
            console.print("[dim]Press Ctrl+C to stop[/]\n")

            for line in container.logs(stream=True, follow=True, tail=tail or 'all'):
                console.print(line.decode('utf-8'), end='')
        else:
            console.print(f"\n[cyan]📜 Logs for: {container_name}[/]\n")

            logs = container.logs(tail=tail or 'all').decode('utf-8')
            console.print(logs)

        return True

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Stopped following logs[/]")
        return True
    except Exception as e:
        error(f"Failed to get logs: {e}")
        return False


# =============================================================================
# VICTIM CONTAINER OPERATIONS
# =============================================================================

def start_victim_container(campaign_id: str, victim_id: str) -> bool:
    """Start victim container"""
    container_name = get_victim_container_name(campaign_id, victim_id)
    console.print(f"\n[cyan]▶️  Starting victim container: {container_name}[/]")

    container = find_container_by_name_pattern(container_name)

    if not container:
        error(f"Container not found: {container_name}")
        info("Victim containers are created dynamically by the backend when a victim accesses the phishing link")
        return False

    try:
        if container.status == 'running':
            info(f"Container already running: {container_name}")
            return True

        container.start()
        success(f"Started container: {container_name}")
        return True

    except Exception as e:
        error(f"Failed to start container: {e}")
        return False


def stop_victim_container(campaign_id: str, victim_id: str) -> bool:
    """Stop victim container"""
    container_name = get_victim_container_name(campaign_id, victim_id)
    console.print(f"\n[cyan]⏸️  Stopping victim container: {container_name}[/]")

    container = find_container_by_name_pattern(container_name)

    if not container:
        warning(f"Container not found: {container_name}")
        return True  # Already stopped/removed

    try:
        if container.status != 'running':
            info(f"Container already stopped: {container_name}")
            return True

        container.stop(timeout=10)
        success(f"Stopped container: {container_name}")
        return True

    except Exception as e:
        error(f"Failed to stop container: {e}")
        return False


def get_victim_container_logs(campaign_id: str, victim_id: str, follow=False, tail=None) -> bool:
    """Show victim container logs"""
    container_name = get_victim_container_name(campaign_id, victim_id)

    container = find_container_by_name_pattern(container_name)

    if not container:
        error(f"Container not found: {container_name}")
        return False

    try:
        if follow:
            console.print(f"\n[cyan]📜 Following logs for: {container_name}[/]")
            console.print("[dim]Press Ctrl+C to stop[/]\n")

            for line in container.logs(stream=True, follow=True, tail=tail or 'all'):
                console.print(line.decode('utf-8'), end='')
        else:
            console.print(f"\n[cyan]📜 Logs for: {container_name}[/]\n")

            logs = container.logs(tail=tail or 'all').decode('utf-8')
            console.print(logs)

        return True

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Stopped following logs[/]")
        return True
    except Exception as e:
        error(f"Failed to get logs: {e}")
        return False
