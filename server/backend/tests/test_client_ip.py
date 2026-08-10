import socket
import unittest
from unittest.mock import patch

from starlette.requests import Request

from utils.client_ip import get_dashboard_client_ip


def build_request(peer_ip: str, real_ip: str | None = None) -> Request:
    headers = []
    if real_ip is not None:
        headers.append((b"x-real-ip", real_ip.encode("ascii")))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/auth/login",
            "headers": headers,
            "client": (peer_ip, 12345),
        }
    )


class DashboardClientIPTests(unittest.TestCase):
    @staticmethod
    def trusted_proxy_result():
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("172.20.0.2", 0),
            )
        ]

    @patch("utils.client_ip.socket.getaddrinfo")
    def test_accepts_real_ip_from_the_frontend_proxy(self, getaddrinfo):
        getaddrinfo.return_value = self.trusted_proxy_result()
        request = build_request("172.20.0.2", "203.0.113.10")

        self.assertEqual(get_dashboard_client_ip(request), "203.0.113.10")

    @patch("utils.client_ip.socket.getaddrinfo")
    def test_ignores_spoofed_header_from_an_untrusted_peer(self, getaddrinfo):
        getaddrinfo.return_value = self.trusted_proxy_result()
        request = build_request("172.20.0.99", "203.0.113.10")

        self.assertEqual(get_dashboard_client_ip(request), "172.20.0.99")

    @patch("utils.client_ip.socket.getaddrinfo")
    def test_invalid_forwarded_address_falls_back_to_proxy(self, getaddrinfo):
        getaddrinfo.return_value = self.trusted_proxy_result()
        request = build_request("172.20.0.2", "$(whoami)")

        self.assertEqual(get_dashboard_client_ip(request), "172.20.0.2")

    @patch(
        "utils.client_ip.socket.getaddrinfo",
        side_effect=socket.gaierror,
    )
    def test_proxy_resolution_failure_is_fail_closed(self, _getaddrinfo):
        request = build_request("172.20.0.2", "203.0.113.10")

        self.assertEqual(get_dashboard_client_ip(request), "172.20.0.2")
