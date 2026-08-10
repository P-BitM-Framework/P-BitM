import os
import docker
import logging
import tarfile
import io

logger = logging.getLogger(__name__)
_docker_client = None


class CampaignRuntimeStateError(RuntimeError):
    """Raised when a campaign runtime cannot be paused or resumed safely."""


def get_docker_client():
    """Connect on first use so backend startup does not race docker-proxy."""
    global _docker_client
    if _docker_client is None:
        _docker_client = docker.from_env()
    return _docker_client

def copy_file_to_container(container_id: str, local_path: str, container_path: str):
    """
    Copy file to container using Docker SDK

    Args:
        container_id: Container ID
        local_path: Local file path
        container_path: Destination path in container (full path including filename)
    """

    container = get_docker_client().containers.get(container_id)

    # Create tar archive in memory
    tar_stream = io.BytesIO()

    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
        # Get filename from container path
        filename = os.path.basename(container_path)

        # Add file to tar with correct name
        tar.add(local_path, arcname=filename)

    tar_stream.seek(0)

    # Get directory path in container
    container_dir = os.path.dirname(container_path)

    # Put archive to container
    container.put_archive(path=container_dir, data=tar_stream)

    return True


def remove_related_containers(container_name, campaign_id=None):
    docker_client = get_docker_client()
    containers = {}

    try:
        container = docker_client.containers.get(container_name)
        containers[container.id] = container
    except docker.errors.NotFound:
        logger.warning(f"Container {container_name} not found during deletion")
    except Exception as e:
        raise RuntimeError(
            f"Unable to inspect campaign container {container_name}"
        ) from e

    if campaign_id:
        related = docker_client.containers.list(
            all=True,
            filters={"label": f"bitm.campaign.id={campaign_id}"},
        )
        for container in related:
            containers[container.id] = container

    failures = []
    for container in containers.values():
        labels = container.labels or {}
        if campaign_id and labels.get("bitm.campaign.id") != campaign_id:
            failures.append(
                f"{container.name}: container is outside campaign scope"
            )
            continue
        try:
            container.remove(force=True)
            logger.info(f"Removed campaign container: {container.name}")
        except docker.errors.NotFound:
            continue
        except Exception as exc:
            logger.error(
                "Error removing campaign container %s: %s",
                container.name,
                exc,
            )
            failures.append(f"{container.name}: {exc}")

    if failures:
        raise RuntimeError("; ".join(failures))

    return len(containers)


def _get_campaign_runtime_containers(container_name, campaign_id):
    """Return only app-owned containers belonging to one campaign."""
    docker_client = get_docker_client()
    containers = {}

    try:
        campaign_container = docker_client.containers.get(container_name)
    except docker.errors.NotFound as exc:
        raise CampaignRuntimeStateError(
            f"Campaign container {container_name} was not found"
        ) from exc

    campaign_labels = campaign_container.labels or {}
    if (
        campaign_labels.get("bitm.campaign.id") != campaign_id
        or campaign_labels.get("bitm.type") != "campaign"
    ):
        raise CampaignRuntimeStateError(
            "Campaign container is outside the requested scope"
        )
    containers[campaign_container.id] = campaign_container

    related = docker_client.containers.list(
        all=True,
        filters={"label": f"bitm.campaign.id={campaign_id}"},
    )
    for container in related:
        labels = container.labels or {}
        is_owned = (
            labels.get("bitm.campaign.id") == campaign_id
            and (
                labels.get("bitm.type") == "campaign"
                or labels.get("bitm.role")
                in {"victim", "campaign-egress-proxy"}
            )
        )
        if is_owned:
            containers[container.id] = container

    return list(containers.values())


def set_campaign_runtime_paused(
    container_name: str,
    campaign_id: str,
    paused: bool,
) -> int:
    """
    Pause or resume every live workload belonging to a campaign.

    Docker pause preserves browser and WebSocket process state. If one
    operation fails, containers already changed by this call are restored to
    their prior state.
    """
    try:
        containers = _get_campaign_runtime_containers(
            container_name,
            campaign_id,
        )
        campaign_container = next(
            container
            for container in containers
            if (container.labels or {}).get("bitm.type") == "campaign"
        )
        campaign_container.reload()
        if campaign_container.status not in {"running", "paused"}:
            raise CampaignRuntimeStateError(
                f"Campaign container is {campaign_container.status}"
            )
    except CampaignRuntimeStateError:
        raise
    except Exception as exc:
        raise CampaignRuntimeStateError(
            "Campaign runtime could not be inspected"
        ) from exc

    def priority(container):
        labels = container.labels or {}
        is_campaign = labels.get("bitm.type") == "campaign"
        if paused:
            return 0 if is_campaign else 1
        return 1 if is_campaign else 0

    changed = []
    try:
        for container in sorted(containers, key=priority):
            container.reload()
            if paused and container.status == "running":
                container.pause()
                changed.append(container)
            elif not paused and container.status == "paused":
                container.unpause()
                changed.append(container)
    except Exception as exc:
        logger.exception(
            "Failed to %s campaign runtime %s",
            "pause" if paused else "resume",
            campaign_id,
        )
        for container in reversed(changed):
            try:
                container.unpause() if paused else container.pause()
            except Exception:
                logger.exception(
                    "Failed to roll back runtime state for %s",
                    container.name,
                )
        raise CampaignRuntimeStateError(
            f"Campaign runtime could not be "
            f"{'paused' if paused else 'resumed'}"
        ) from exc

    return len(changed)


def set_campaign_runtime_started(
    container_name: str,
    campaign_id: str,
    started: bool,
) -> int:
    """
    Start or stop the persisted runtime for a scheduled campaign.

    Supporting sidecars start before the public gateway and stop after it.
    Partial changes are rolled back so a failed activation can be retried.
    """
    try:
        containers = _get_campaign_runtime_containers(
            container_name,
            campaign_id,
        )
    except CampaignRuntimeStateError:
        raise
    except Exception as exc:
        raise CampaignRuntimeStateError(
            "Campaign runtime could not be inspected"
        ) from exc

    def priority(container):
        is_campaign = (container.labels or {}).get("bitm.type") == "campaign"
        if started:
            return 1 if is_campaign else 0
        return 0 if is_campaign else 1

    changed = []
    try:
        for container in sorted(containers, key=priority):
            container.reload()
            if started and container.status in {"created", "exited"}:
                container.start()
                changed.append(container)
            elif not started and container.status in {"running", "paused"}:
                container.stop(timeout=10)
                changed.append(container)
    except Exception as exc:
        logger.exception(
            "Failed to %s scheduled campaign runtime %s",
            "start" if started else "stop",
            campaign_id,
        )
        for container in reversed(changed):
            try:
                if started:
                    container.stop(timeout=10)
                else:
                    container.start()
            except Exception:
                logger.exception(
                    "Failed to roll back scheduled runtime state for %s",
                    container.name,
                )
        raise CampaignRuntimeStateError(
            f"Scheduled campaign runtime could not be "
            f"{'started' if started else 'stopped'}"
        ) from exc

    return len(changed)


def get_container(container_name):
    try:
        container = get_docker_client().containers.get(container_name)
        return container
    except docker.errors.NotFound:
        logger.error(f"Container {container_name} not found")
        raise
    except Exception as e:
        logger.error(f"Error retrieving container {container_name}: {e}")
        raise
