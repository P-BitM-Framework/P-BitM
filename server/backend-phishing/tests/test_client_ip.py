import ipaddress
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.client_ip import get_public_client_ip


_REAL_IP_ADDRESS = ipaddress.ip_address
_DOCUMENTATION_NETWORKS = (
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
)


class DocumentationAddress:
    """Treat TEST-NET addresses as public without using operational IPs."""

    def __init__(self, value: str):
        self.address = _REAL_IP_ADDRESS(value)

    def __str__(self) -> str:
        return str(self.address)

    @property
    def is_private(self) -> bool:
        if any(self.address in network for network in _DOCUMENTATION_NETWORKS):
            return False
        return self.address.is_private

    @property
    def is_loopback(self) -> bool:
        return self.address.is_loopback

    @property
    def is_link_local(self) -> bool:
        return self.address.is_link_local

    @property
    def is_unspecified(self) -> bool:
        return self.address.is_unspecified


def documentation_ip_address(value: str) -> DocumentationAddress:
    return DocumentationAddress(value)


def connection(
    *,
    peer_ip: str,
    forwarded_for: str | None = None,
):
    headers = {}
    if forwarded_for is not None:
        headers["x-forwarded-for"] = forwarded_for
    return SimpleNamespace(
        client=SimpleNamespace(host=peer_ip),
        headers=headers,
    )


class PublicClientIPTests(unittest.TestCase):
    def test_accepts_forwarded_ip_from_local_nginx(self):
        request = connection(
            peer_ip="127.0.0.1",
            forwarded_for="198.51.100.40, 172.20.0.5",
        )

        self.assertEqual(
            get_public_client_ip(request),
            "198.51.100.40",
        )

    def test_accepts_forwarded_ip_from_ipv6_loopback(self):
        request = connection(
            peer_ip="::1",
            forwarded_for="2001:db8::8888, 172.20.0.5",
        )

        self.assertEqual(
            get_public_client_ip(request),
            "2001:db8::8888",
        )

    def test_uses_rightmost_public_address_before_internal_proxies(self):
        request = connection(
            peer_ip="127.0.0.1",
            forwarded_for="198.51.100.174, 198.51.100.40, 172.20.0.5",
        )

        with patch(
            "core.client_ip.ipaddress.ip_address",
            side_effect=documentation_ip_address,
        ):
            self.assertEqual(get_public_client_ip(request), "198.51.100.40")

    def test_ignores_spoofed_header_from_non_loopback_peer(self):
        request = connection(
            peer_ip="172.30.0.8",
            forwarded_for="203.0.113.20",
        )

        self.assertEqual(
            get_public_client_ip(request),
            "172.30.0.8",
        )

    def test_invalid_forwarded_ip_falls_back_to_the_socket_peer(self):
        request = connection(
            peer_ip="127.0.0.1",
            forwarded_for="$(whoami)",
        )

        self.assertEqual(
            get_public_client_ip(request),
            "127.0.0.1",
        )
