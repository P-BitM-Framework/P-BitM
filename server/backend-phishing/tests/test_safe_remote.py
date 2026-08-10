import socket
import unittest
from unittest.mock import patch

from utils.safe_remote import (
    UnsafeRemoteURLError,
    validate_public_http_url,
)


def address_record(address: str, port: int = 443):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    sockaddr = (address, port, 0, 0) if family == socket.AF_INET6 else (address, port)
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr)


class PublicRemoteURLTests(unittest.TestCase):
    def test_public_hostname_is_normalized(self):
        with patch(
            "utils.safe_remote._resolve_public_addresses",
            return_value=["203.0.113.34"],
        ):
            result = validate_public_http_url(
                "https://Example.COM/path?value=1#fragment"
            )

        self.assertEqual(result, "https://example.com/path?value=1")

    def test_private_and_metadata_addresses_are_rejected(self):
        for address in (
            "127.0.0.1",
            "10.0.0.10",
            "172.16.0.10",
            "192.168.1.10",
            "169.254.169.254",
            "::1",
        ):
            with self.subTest(address=address), patch(
                "utils.safe_remote.socket.getaddrinfo",
                return_value=[address_record(address)],
            ):
                with self.assertRaises(UnsafeRemoteURLError):
                    validate_public_http_url("https://target.example/")

    def test_mixed_public_and_private_dns_answer_is_rejected(self):
        with patch(
            "utils.safe_remote.socket.getaddrinfo",
            return_value=[
                address_record("93.184.216.34"),
                address_record("10.0.0.10"),
            ],
        ):
            with self.assertRaises(UnsafeRemoteURLError):
                validate_public_http_url("https://target.example/")

    def test_credentials_and_non_http_schemes_are_rejected(self):
        for url in (
            "file:///etc/passwd",
            "ftp://example.com/file",
            "https://user:password@example.com/",
        ):
            with self.subTest(url=url), self.assertRaises(UnsafeRemoteURLError):
                validate_public_http_url(url)


if __name__ == "__main__":
    unittest.main()
