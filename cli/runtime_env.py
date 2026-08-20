"""Small, dependency-free helpers for generated runtime environments."""

from pathlib import Path


SECRET_PLACEHOLDER_MARKERS = (
    "change-me",
    "changeme",
    "replace-with",
    "example",
)


def is_secure_runtime_secret(value: str, minimum_length: int) -> bool:
    if not isinstance(value, str) or len(value) < minimum_length:
        return False
    lowered = value.lower()
    return not any(marker in lowered for marker in SECRET_PLACEHOLDER_MARKERS)


def get_runtime_env_errors(values: dict) -> list:
    errors = []
    if values.get("ENVIRONMENT") not in {"development", "production"}:
        errors.append("invalid ENVIRONMENT")
    if not values.get("ADMIN_USERNAME", "").strip():
        errors.append("missing ADMIN_USERNAME")
    for name, minimum_length in (
        ("ADMIN_PASSWORD", 16),
        ("INTERNAL_API_KEY", 32),
        ("DATA_ENCRYPTION_KEY", 32),
    ):
        if not is_secure_runtime_secret(values.get(name, ""), minimum_length):
            errors.append(f"unsafe {name}")
    for name in ("HOST_STORAGE_PATH", "IP"):
        if not values.get(name, "").strip():
            errors.append(f"missing {name}")
    for name in ("PBITM_UID", "PBITM_GID"):
        value = values.get(name, "")
        if not value.isdecimal() or not 1 <= int(value, 10) <= 2_147_483_647:
            errors.append(f"invalid {name}")
    return errors


def read_env_file(env_file=None) -> dict:
    """Read a simple KEY=VALUE environment file into a dictionary."""
    project_root = Path(__file__).parent.parent.resolve()
    env_file = Path(env_file) if env_file else project_root / "server" / ".env"
    if not env_file.is_absolute():
        env_file = project_root / env_file
    env_vars = {}

    if not env_file.exists():
        return env_vars

    with env_file.open("r") as env_handle:
        for line in env_handle:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    return env_vars
