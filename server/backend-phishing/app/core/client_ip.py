"""Resolve client IPs received through the local nginx gateway."""

from __future__ import annotations

import ipaddress
from typing import Any


def normalize_ip_address(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def get_public_client_ip(connection: Any) -> str:
    direct_ip = normalize_ip_address(
        connection.client.host if connection.client else None
    )
    fallback = direct_ip or "unknown"

    if not direct_ip or not ipaddress.ip_address(direct_ip).is_loopback:
        return fallback

    forwarded_for = connection.headers.get("x-forwarded-for", "")
    forwarded_ips = [
        normalized
        for value in forwarded_for.split(",")
        if (normalized := normalize_ip_address(value))
    ]

    # nginx appends Traefik to the right of the chain. Walk backwards so an
    # arbitrary value prepended by a client or upstream cannot win.
    for forwarded_ip in reversed(forwarded_ips):
        address = ipaddress.ip_address(forwarded_ip)
        if not (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_unspecified
        ):
            return forwarded_ip

    return forwarded_ips[0] if forwarded_ips else fallback
