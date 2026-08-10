from __future__ import annotations

import base64
import binascii
import re
import struct
from urllib.parse import urlsplit

from utils.safe_remote import safe_get_public_url


MAX_FAVICON_CHARACTERS = 256 * 1024
MAX_FAVICON_DECODED_BYTES = 190 * 1024
ALLOWED_FAVICON_DATA_TYPES = {
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/vnd.microsoft.icon",
    "image/webp",
    "image/x-icon",
}


def validate_favicon_url(value: str) -> str:
    if not value:
        return value
    if len(value) > 2_048:
        raise ValueError("favicon URL is too large")

    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("favicon must use a credential-free HTTP(S) URL")
    return value


def detect_favicon_media_type(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if (
        len(content) >= 12
        and content.startswith(b"RIFF")
        and content[8:12] == b"WEBP"
    ):
        return "image/webp"
    if content.startswith(b"\x00\x00\x01\x00"):
        return "image/x-icon"
    return None


def extract_largest_png_from_ico(content: bytes) -> bytes | None:
    """Return the largest valid embedded PNG frame from an ICO container."""
    if len(content) < 6 or not content.startswith(b"\x00\x00\x01\x00"):
        return None

    image_count = struct.unpack_from("<H", content, 4)[0]
    if image_count < 1 or image_count > 256:
        return None

    directory_end = 6 + image_count * 16
    if directory_end > len(content):
        return None

    candidates: list[tuple[int, bytes]] = []
    for index in range(image_count):
        entry_offset = 6 + index * 16
        image_size, image_offset = struct.unpack_from(
            "<II",
            content,
            entry_offset + 8,
        )
        image_end = image_offset + image_size
        if (
            image_size < 24
            or image_offset < directory_end
            or image_end > len(content)
        ):
            continue

        image = content[image_offset:image_end]
        if (
            not image.startswith(b"\x89PNG\r\n\x1a\n")
            or image[12:16] != b"IHDR"
        ):
            continue

        width, height = struct.unpack_from(">II", image, 16)
        if not (1 <= width <= 1024 and 1 <= height <= 1024):
            continue
        candidates.append((width * height, image))

    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate[0])[1]


def validate_favicon_data_uri(value: str) -> str:
    if not value:
        return value
    if len(value) > MAX_FAVICON_CHARACTERS:
        raise ValueError("favicon data URI is too large")

    header, separator, encoded_data = value.partition(",")
    if not separator or not header.lower().startswith("data:"):
        raise ValueError("favicon must be a supported image data URI")

    metadata = [item.strip().lower() for item in header[5:].split(";")]
    if (
        not metadata
        or metadata[0] not in ALLOWED_FAVICON_DATA_TYPES
        or "base64" not in metadata[1:]
    ):
        raise ValueError("unsupported favicon data URI")

    try:
        decoded = base64.b64decode(encoded_data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid base64 favicon data") from exc
    if not decoded or len(decoded) > MAX_FAVICON_DECODED_BYTES:
        raise ValueError("favicon image is empty or too large")

    detected_type = detect_favicon_media_type(decoded)
    declared_type = metadata[0]
    compatible_types = (
        {"image/x-icon", "image/vnd.microsoft.icon"}
        if detected_type == "image/x-icon"
        else {detected_type}
    )
    if detected_type is None or declared_type not in compatible_types:
        raise ValueError("favicon content does not match a supported image type")

    # Firefox can expose ICO data URIs whose directory dimensions do not match
    # their embedded PNG frames. Browsers and image converters handle these
    # inconsistently, so use the largest actual PNG frame directly.
    if detected_type == "image/x-icon":
        png_frame = extract_largest_png_from_ico(decoded)
        if png_frame is not None:
            encoded_png = base64.b64encode(png_frame).decode("ascii")
            return validate_favicon_data_uri(
                f"data:image/png;base64,{encoded_png}"
            )
    return value


def favicon_bytes_to_data_uri(content: bytes, content_type: str) -> str:
    if not content or len(content) > MAX_FAVICON_DECODED_BYTES:
        raise ValueError("favicon image is empty or too large")

    media_type = detect_favicon_media_type(content)
    if media_type is None:
        raise ValueError("unsupported favicon image content")

    encoded = base64.b64encode(content).decode("ascii")
    return validate_favicon_data_uri(f"data:{media_type};base64,{encoded}")


def fetch_public_favicon_data_uri(url: str) -> str:
    response = safe_get_public_url(
        validate_favicon_url(url),
        timeout=3,
        max_bytes=MAX_FAVICON_DECODED_BYTES,
    )
    if response.status_code != 200:
        raise ValueError("favicon URL did not return a successful response")
    return favicon_bytes_to_data_uri(
        response.content,
        response.headers.get("content-type", ""),
    )


def remove_empty_favicon_placeholders(html_content: str) -> str:
    """Remove favicon elements instead of turning an empty URL into this page."""
    patterns = (
        r"<link\b(?=[^>]*\bFAVICON\b)"
        r"(?=[^>]*\brel\s*=\s*['\"]?icon\b)[^>]*>",
        r"<img\b(?=[^>]*\bFAVICON\b)"
        r"(?=[^>]*\bheading-favicon\b)[^>]*>",
    )
    for pattern in patterns:
        html_content = re.sub(
            pattern,
            "",
            html_content,
            flags=re.IGNORECASE,
        )
    return html_content
