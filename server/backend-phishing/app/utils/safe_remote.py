"""Small, pinned HTTP client for cosmetic fetches from public targets."""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import SplitResult, urljoin, urlsplit, urlunsplit


class UnsafeRemoteURLError(ValueError):
    """Raised when a URL could reach a non-public network or is malformed."""


@dataclass(frozen=True)
class SafeRemoteResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes

    @property
    def text(self) -> str:
        content_type = self.headers.get("content-type", "")
        charset = "utf-8"
        for item in content_type.split(";")[1:]:
            key, separator, value = item.strip().partition("=")
            if separator and key.lower() == "charset" and value.strip():
                charset = value.strip().strip("\"'")
                break
        try:
            return self.content.decode(charset, errors="replace")
        except LookupError:
            return self.content.decode("utf-8", errors="replace")


def _parse_public_http_url(url: str) -> tuple[SplitResult, str, int]:
    if not isinstance(url, str) or not url or len(url) > 2_048:
        raise UnsafeRemoteURLError("Invalid remote URL")

    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise UnsafeRemoteURLError("Only credential-free HTTP(S) URLs are allowed")

    try:
        hostname = parsed.hostname.encode("idna").decode("ascii").lower()
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except (UnicodeError, ValueError) as exc:
        raise UnsafeRemoteURLError("Invalid remote host or port") from exc

    return parsed, hostname, port


def _resolve_public_addresses(hostname: str, port: int) -> list[str]:
    try:
        records = socket.getaddrinfo(
            hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise UnsafeRemoteURLError("Remote hostname could not be resolved") from exc

    addresses: list[str] = []
    for record in records:
        raw_address = record[4][0]
        try:
            address = ipaddress.ip_address(raw_address)
        except ValueError as exc:
            raise UnsafeRemoteURLError("Remote hostname returned an invalid address") from exc
        if not address.is_global:
            raise UnsafeRemoteURLError(
                "Remote hostname resolves to a non-public address"
            )
        normalized = str(address)
        if normalized not in addresses:
            addresses.append(normalized)

    if not addresses:
        raise UnsafeRemoteURLError("Remote hostname returned no usable addresses")
    return addresses


def validate_public_http_url(url: str) -> str:
    """Validate and normalize a URL without making an HTTP request."""
    parsed, hostname, port = _parse_public_http_url(url)
    _resolve_public_addresses(hostname, port)

    default_port = 443 if parsed.scheme == "https" else 80
    host = f"[{hostname}]" if ":" in hostname else hostname
    netloc = host if port == default_port else f"{host}:{port}"
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme, netloc, path, parsed.query, ""))


def _request_pinned(
    url: str,
    *,
    timeout: float,
    max_bytes: int,
) -> SafeRemoteResponse:
    parsed, hostname, port = _parse_public_http_url(url)
    addresses = _resolve_public_addresses(hostname, port)
    address = addresses[0]

    raw_socket = socket.create_connection((address, port), timeout=timeout)
    connection: http.client.HTTPConnection | None = None
    try:
        if parsed.scheme == "https":
            context = ssl.create_default_context()
            raw_socket = context.wrap_socket(
                raw_socket,
                server_hostname=hostname,
            )

        connection = http.client.HTTPConnection(
            hostname,
            port=port,
            timeout=timeout,
        )
        connection.sock = raw_socket

        default_port = 443 if parsed.scheme == "https" else 80
        host_header = f"[{hostname}]" if ":" in hostname else hostname
        if port != default_port:
            host_header = f"{host_header}:{port}"
        request_target = parsed.path or "/"
        if parsed.query:
            request_target = f"{request_target}?{parsed.query}"

        connection.request(
            "GET",
            request_target,
            headers={
                "Host": host_header,
                "User-Agent": "P-BITM metadata fetcher",
                "Accept": "text/html,image/*;q=0.8,*/*;q=0.1",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
        )
        response = connection.getresponse()
        content = response.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise UnsafeRemoteURLError("Remote response exceeds the size limit")

        return SafeRemoteResponse(
            status_code=response.status,
            headers={key.lower(): value for key, value in response.getheaders()},
            content=content,
        )
    except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
        raise UnsafeRemoteURLError("Remote request failed") from exc
    finally:
        if connection is not None:
            connection.close()
        else:
            raw_socket.close()


def safe_get_public_url(
    url: str,
    *,
    timeout: float = 5,
    max_bytes: int = 1_048_576,
    max_redirects: int = 3,
) -> SafeRemoteResponse:
    """GET a public URL while revalidating and pinning every redirect hop."""
    current_url = validate_public_http_url(url)
    for redirect_count in range(max_redirects + 1):
        response = _request_pinned(
            current_url,
            timeout=timeout,
            max_bytes=max_bytes,
        )
        if response.status_code not in {301, 302, 303, 307, 308}:
            return response

        location = response.headers.get("location")
        if not location or redirect_count >= max_redirects:
            raise UnsafeRemoteURLError("Invalid or excessive redirect chain")
        current_url = validate_public_http_url(urljoin(current_url, location))

    raise UnsafeRemoteURLError("Excessive redirect chain")
