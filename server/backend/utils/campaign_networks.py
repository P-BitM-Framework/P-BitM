"""Lifecycle helpers for campaign-scoped Docker networks."""

from __future__ import annotations

import re

import docker

from utils.docker import get_docker_client


CAMPAIGN_ID_PATTERN = re.compile(r"^[0-9a-f]{8}$")
NETWORK_PREFIX = "pbitm-campaign-"
EGRESS_NETWORK_PREFIX = "pbitm-egress-"


def campaign_network_name(campaign_id: str) -> str:
    """Return the deterministic private-network name for a campaign."""
    if not CAMPAIGN_ID_PATTERN.fullmatch(campaign_id):
        raise ValueError("Invalid campaign ID")
    return f"{NETWORK_PREFIX}{campaign_id}"


def campaign_egress_network_name(campaign_id: str) -> str:
    if not CAMPAIGN_ID_PATTERN.fullmatch(campaign_id):
        raise ValueError("Invalid campaign ID")
    return f"{EGRESS_NETWORK_PREFIX}{campaign_id}"


def _validate_network_scope(network, campaign_id: str) -> None:
    labels = network.attrs.get("Labels") or {}
    if (
        labels.get("bitm.campaign.id") != campaign_id
        or labels.get("bitm.role") != "campaign-private"
    ):
        raise RuntimeError(
            f"Network name collision for campaign {campaign_id}"
        )
    if network.attrs.get("Internal") is not True:
        raise RuntimeError(
            f"Campaign network {network.name} predates isolated egress; "
            "recreate the campaign runtime"
        )


def ensure_campaign_network(campaign_id: str):
    """
    Return the campaign network, creating it when needed.

    Victims have no direct route to the host or Internet. Firefox reaches public
    targets through the campaign gateway's filtered forward proxy, while local
    collection continues over the private campaign network.
    """
    network_name = campaign_network_name(campaign_id)
    docker_client = get_docker_client()

    try:
        network = docker_client.networks.get(network_name)
        _validate_network_scope(network, campaign_id)
        return network
    except docker.errors.NotFound:
        try:
            return docker_client.networks.create(
                network_name,
                driver="bridge",
                attachable=False,
                internal=True,
                labels={
                    "bitm.campaign.id": campaign_id,
                    "bitm.role": "campaign-private",
                },
            )
        except docker.errors.APIError as exc:
            if exc.status_code != 409:
                raise
            network = docker_client.networks.get(network_name)
            _validate_network_scope(network, campaign_id)
            return network


def ensure_campaign_egress_network(campaign_id: str):
    """Create the Internet-facing network used only by the egress sidecar."""
    network_name = campaign_egress_network_name(campaign_id)
    docker_client = get_docker_client()
    try:
        network = docker_client.networks.get(network_name)
        labels = network.attrs.get("Labels") or {}
        if (
            labels.get("bitm.campaign.id") != campaign_id
            or labels.get("bitm.role") != "campaign-egress"
            or network.attrs.get("Internal") is True
        ):
            raise RuntimeError(f"Invalid egress network {network_name}")
        return network
    except docker.errors.NotFound:
        return docker_client.networks.create(
            network_name,
            driver="bridge",
            attachable=False,
            internal=False,
            labels={
                "bitm.campaign.id": campaign_id,
                "bitm.role": "campaign-egress",
            },
        )


def connect_container_to_campaign_network(container, campaign_id: str):
    """Idempotently connect a validated container to its campaign network."""
    labels = container.labels or {}
    if labels.get("bitm.campaign.id") != campaign_id:
        raise RuntimeError("Refusing to connect a container outside the campaign")

    network = ensure_campaign_network(campaign_id)
    container.reload()
    connected_networks = container.attrs.get("NetworkSettings", {}).get(
        "Networks", {}
    )
    if network.name not in connected_networks:
        network.connect(container)
        container.reload()
    return network


def remove_campaign_network(campaign_id: str) -> bool:
    """Remove only the validated network belonging to the given campaign."""
    network_name = campaign_network_name(campaign_id)
    docker_client = get_docker_client()

    try:
        network = docker_client.networks.get(network_name)
    except docker.errors.NotFound:
        return False

    _validate_network_scope(network, campaign_id)
    network.reload()
    if network.attrs.get("Containers"):
        raise RuntimeError(
            f"Campaign network {network_name} still has attached containers"
        )
    network.remove()
    return True


def remove_campaign_egress_network(campaign_id: str) -> bool:
    network_name = campaign_egress_network_name(campaign_id)
    docker_client = get_docker_client()
    try:
        network = docker_client.networks.get(network_name)
    except docker.errors.NotFound:
        return False
    labels = network.attrs.get("Labels") or {}
    if (
        labels.get("bitm.campaign.id") != campaign_id
        or labels.get("bitm.role") != "campaign-egress"
    ):
        raise RuntimeError(f"Invalid egress network {network_name}")
    network.reload()
    if network.attrs.get("Containers"):
        raise RuntimeError(f"Egress network {network_name} is still in use")
    network.remove()
    return True
