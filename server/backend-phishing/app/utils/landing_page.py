import logging
from html import escape
from pathlib import Path

logger = logging.getLogger(__name__)


def replace_variables(
    text: str,
    victim: dict,
    target_url: str = ""
) -> str:
    """
    Replace template variables with actual values.

    Available variables:
    - {{first_name}}
    - {{last_name}}
    - {{email}}
    - {{position}}
    - {{company}}
    - {{target_url}}
    """

    if not text:
        return ""

    replacements = {
        "{{first_name}}": victim.get("first_name", "User"),
        "{{last_name}}": victim.get("last_name", ""),
        "{{email}}": victim.get("email", ""),
        "{{position}}": victim.get("position", "") or "",
        "{{company}}": victim.get("company", "") or "",
        "{{target_url}}": target_url,
    }

    result = text
    for key, value in replacements.items():
        result = result.replace(
            key,
            escape(str(value), quote=True),
        )

    return result


def get_template_content(template_name: str) -> str:
    """Load HTML/JS template content from file (templates/ for HTML, static/ for JS)."""
    app_dir = Path(__file__).parent.parent
    subdir = "static" if template_name.endswith(".js") else "templates"
    file_path = app_dir / subdir / template_name
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except OSError as e:
        logger.error("Error loading template %s: %s", template_name, e)
        return ""
