"""Provision a campaign-scoped forward-proxy sidecar."""

from __future__ import annotations

import os

from utils.campaign_networks import (
    ensure_campaign_egress_network,
    ensure_campaign_network,
)
from utils.docker import get_docker_client


EGRESS_IMAGE = os.getenv("EGRESS_IMAGE", "p-bitm-egress:latest")


def create_campaign_egress_proxy(
    campaign_id: str,
    *,
    start: bool = True,
):
    private_network = ensure_campaign_network(campaign_id)
    external_network = ensure_campaign_egress_network(campaign_id)
    name = f"p-bitm-egress-{campaign_id}"
    container = get_docker_client().containers.create(
        image=EGRESS_IMAGE,
        name=name,
        detach=True,
        labels={
            "bitm.campaign.id": campaign_id,
            "bitm.role": "campaign-egress-proxy",
            "traefik.enable": "false",
        },
        network=external_network.name,
        security_opt=["no-new-privileges:true"],
        cap_drop=["ALL"],
        read_only=True,
        tmpfs={
            "/run": "rw,noexec,nosuid,mode=1777,size=8m",
            "/var/cache/squid": "rw,noexec,nosuid,mode=1777,size=32m",
            "/var/spool/squid": "rw,noexec,nosuid,mode=1777,size=32m",
        },
        pids_limit=128,
        mem_limit="256m",
        memswap_limit="256m",
        init=True,
        auto_remove=False,
    )
    private_network.connect(container)
    if start:
        container.start()
    return container
