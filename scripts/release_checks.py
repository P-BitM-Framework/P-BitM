#!/usr/bin/env python3
"""Repository-only release checks that require no third-party packages."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
HISTORICAL_RELEASE_PATHS = (
    ROOT / "bitm-images/selkies-v1",
    ROOT / "bitm-images/selkies-v2",
)

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
MARKDOWN_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
SECRET_PATTERNS = {
    "private key": re.compile(
        rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
    "OpenAI-style key": re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    "Slack token": re.compile(rb"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "Google API key": re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
}
EXCLUDED_DIRECTORIES = {
    ".git",
    ".secrets",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "certs",
    "coverage",
    "dist",
    "node_modules",
    "storage",
}
EXCLUDED_SECRET_FILES = {
    "package-lock.json",
}
EXCLUDED_SECRET_SUFFIXES = {
    ".crt",
    ".key",
    ".p12",
    ".pem",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def markdown_files() -> list[Path]:
    files = [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
        ROOT / "THIRD_PARTY_NOTICES.md",
    ]
    files.extend(sorted(DOCS.rglob("*.md")))
    return [path for path in files if path.is_file()]


def validate_markdown_links(files: list[Path]) -> None:
    missing: list[str] = []
    for path in files:
        for raw_target in MARKDOWN_LINK.findall(path.read_text(encoding="utf-8")):
            target = raw_target.strip().split()[0].strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target = unquote(target.split("#", 1)[0])
            if not target:
                continue
            resolved = (
                ROOT / target.lstrip("/")
                if target.startswith("/")
                else path.parent / target
            ).resolve()
            if not resolved.exists():
                missing.append(f"{path.relative_to(ROOT)} -> {raw_target}")
    if missing:
        fail("missing Markdown links:\n  " + "\n  ".join(missing))


def validate_headings(files: list[Path]) -> None:
    duplicates: list[str] = []
    for path in files:
        seen: set[str] = set()
        for _, heading in MARKDOWN_HEADING.findall(path.read_text(encoding="utf-8")):
            normalized = re.sub(r"[^a-z0-9 -]", "", heading.lower())
            normalized = normalized.strip().replace(" ", "-")
            if normalized in seen:
                duplicates.append(f"{path.relative_to(ROOT)}: {heading}")
            seen.add(normalized)
    if duplicates:
        fail("duplicate Markdown headings:\n  " + "\n  ".join(duplicates))


def validate_documentation_navigation() -> None:
    summary_path = DOCS / "SUMMARY.md"
    summary = summary_path.read_text(encoding="utf-8")
    listed = {
        (DOCS / unquote(target.strip().split()[0].strip("<>").split("#", 1)[0])).resolve()
        for target in MARKDOWN_LINK.findall(summary)
        if target and not target.startswith(("#", "http://", "https://", "mailto:"))
    }
    pages = {path.resolve() for path in DOCS.rglob("*.md")}
    unlisted = sorted(pages - listed - {summary_path.resolve()})
    if unlisted:
        fail(
            "documentation pages missing from SUMMARY.md:\n  "
            + "\n  ".join(str(path.relative_to(ROOT)) for path in unlisted)
        )


def repository_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(ROOT).parts
        if any(part in EXCLUDED_DIRECTORIES for part in relative_parts):
            continue
        files.append(path)
    return files


def scan_for_secrets() -> None:
    findings: list[str] = []
    for path in repository_files():
        if (
            path.name in EXCLUDED_SECRET_FILES
            or path.name == ".env"
            or path.name.startswith(".env.")
            or path.name.endswith(".env")
            or path.suffix.lower() in EXCLUDED_SECRET_SUFFIXES
            or path.stat().st_size > 2 * 1024 * 1024
        ):
            continue
        content = path.read_bytes()
        if b"\x00" in content:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{path.relative_to(ROOT)}: {label}")
    if findings:
        fail("possible secrets detected:\n  " + "\n  ".join(findings))


def validate_release_layout() -> None:
    present = [
        str(path.relative_to(ROOT))
        for path in HISTORICAL_RELEASE_PATHS
        if path.exists()
    ]
    if present:
        fail(
            "historical Selkies directories must stay outside the release: "
            + ", ".join(present)
        )

    campaign_config = (
        ROOT / "server/backend-phishing/app/config.py"
    ).read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    if 'Literal["vnc", "selkies"]' not in campaign_config:
        fail("campaign backend protocol contract is not vnc/selkies")
    if "CAMPAIGN_PROTOCOL: selkies" not in workflow:
        fail("CI does not use the canonical Selkies campaign protocol")

    for relative_path in (
        "server/traefik/traefik.yml",
        "server/traefik/traefik.prod.template.yml",
    ):
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        if not re.search(r"(?m)^ping:\s*\{\}\s*$", content):
            fail(f"{relative_path} does not enable the Traefik ping endpoint")


def main() -> None:
    files = markdown_files()
    validate_markdown_links(files)
    validate_headings(files)
    validate_documentation_navigation()
    scan_for_secrets()
    validate_release_layout()
    print(
        f"Release checks passed: {len(files)} Markdown files, documentation navigation, "
        "secret scan, release layout, and protocol contract."
    )


if __name__ == "__main__":
    main()
