"""Resolve a client address only through explicitly trusted reverse proxies."""

from __future__ import annotations

import ipaddress
import os
import socket

from fastapi import Request


def normalize_ip_address(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def _trusted_dashboard_proxy_ips() -> set[str]:
    hostnames = os.getenv("TRUSTED_DASHBOARD_PROXY_HOSTS", "frontend").split(",")
    addresses: set[str] = set()
    for hostname in (value.strip() for value in hostnames):
        if not hostname:
            continue
        try:
            for result in socket.getaddrinfo(hostname, None):
                normalized = normalize_ip_address(result[4][0])
                if normalized:
                    addresses.add(normalized)
        except socket.gaierror:
            continue
    return addresses


def get_dashboard_client_ip(request: Request) -> str:
    """Trust nginx's client header only when the direct peer is the frontend."""
    peer_ip = normalize_ip_address(request.client.host if request.client else None)
    if not peer_ip:
        return "unknown"

    if peer_ip not in _trusted_dashboard_proxy_ips():
        return peer_ip

    forwarded_ip = normalize_ip_address(request.headers.get("x-real-ip"))
    return forwarded_ip or peer_ip
