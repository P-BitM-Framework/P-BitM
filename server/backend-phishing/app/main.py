"""Campaign backend application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import settings
from core.body_limit import RequestBodyLimitMiddleware
from core.websocket_manager import ws_manager
from routes.private import api_router, raw_router
from routes.public import public_router
from routes.tracking import tracking_dispatcher, tracking_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def public_lifespan(_app: FastAPI):
    """Start and stop background work owned by the public application."""
    logger.info("Starting campaign public application")
    await tracking_dispatcher.start()
    await ws_manager.start_ping_loop()
    try:
        yield
    finally:
        logger.info("Stopping campaign public application")
        await ws_manager.stop_ping_loop()
        await tracking_dispatcher.stop()


public_app = FastAPI(
    title="BITM Campaign - Public",
    version="2.0",
    lifespan=public_lifespan,
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)
public_app.add_middleware(
    RequestBodyLimitMiddleware,
    max_bytes=2 * 1024 * 1024,
)
public_app.include_router(public_router)


@public_app.get("/health")
async def public_health():
    """Report public campaign endpoint availability."""
    return {"status": "healthy", "service": "public"}


static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    public_app.mount(
        "/static",
        StaticFiles(directory=str(static_dir)),
        name="static",
    )
    logger.info("Mounted static files from %s", static_dir)
else:
    logger.warning("Static directory not found: %s", static_dir)

# Registered last: tracking_router's catch-all GET /{requested_path:path}
# would otherwise shadow both /health and the /static mount, since
# Starlette matches routes (including mounts) in registration order.
public_app.include_router(tracking_router)


api_app = FastAPI(
    title="BITM Campaign - API",
    version="2.0",
)
api_app.add_middleware(
    RequestBodyLimitMiddleware,
    max_bytes=11 * 1024 * 1024,
)
api_app.include_router(api_router)
api_app.include_router(raw_router)


@api_app.get("/health")
async def api_health():
    """Report internal API and WebSocket manager state."""
    return {
        "status": "healthy",
        "service": "api",
        "stats": ws_manager.get_stats(),
        "ping_loop": {"running": ws_manager.ping_loop_running},
    }


async def run_public() -> None:
    """Serve the public application behind nginx and Traefik."""
    server = uvicorn.Server(
        uvicorn.Config(
            public_app,
            host="127.0.0.1",
            port=8443,
            log_level="info",
            access_log=False,
            proxy_headers=False,
            ws_max_size=settings.WS_MAX_MESSAGE_BYTES,
            ws_max_queue=settings.WS_MAX_QUEUE,
            ws_per_message_deflate=False,
        )
    )
    await server.serve()


async def run_api() -> None:
    """Serve the internal campaign API."""
    server = uvicorn.Server(
        uvicorn.Config(
            api_app,
            host="0.0.0.0",
            port=8080,
            log_level="info",
        )
    )
    await server.serve()


async def main() -> None:
    """Run the public and internal servers concurrently."""
    logger.info("Starting campaign backend")
    logger.info("Public application listening on port 8443")
    logger.info("Internal API listening on port 8080")
    await asyncio.gather(run_public(), run_api())


if __name__ == "__main__":
    asyncio.run(main())
