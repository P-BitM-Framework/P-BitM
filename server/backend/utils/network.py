import socket
import random
from urllib.parse import urlparse


def find_free_port(start=8000, end=8999):
    ports = list(range(start, end + 1))
    random.shuffle(ports)
    for p in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", p))
                return p
            except OSError:
                continue
    raise RuntimeError("no free port found in range")


def valid_url(u: str) -> bool:
    if not isinstance(u, str) or not u or u != u.strip():
        return False
    if len(u) > 2048:
        return False
    if any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in u):
        return False
    if "\\" in u or any(sequence in u for sequence in ("`", "$(", "${")):
        return False

    try:
        parsed = urlparse(u)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        # Accessing port validates malformed and out-of-range values.
        parsed.port
        return True
    except (TypeError, ValueError):
        return False
