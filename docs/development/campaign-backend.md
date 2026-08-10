# Campaign backend

One campaign service is created for each active campaign. It combines nginx
with public and private FastAPI applications.

## Configuration

`server/backend-phishing/app/config.py` is the authoritative environment
contract. Application code should use the shared `settings` instance instead
of reading environment variables independently.

`ADMIN_API_URL` is the canonical admin endpoint. `DB_PATH` is a filesystem
path, not a SQLAlchemy URL.

## Trust separation

- Public routes handle campaign entry, tracking admission, and WebSockets.
- Private routes handle authenticated local collection and admin exchanges.
- The service does not receive Docker socket access.
- Calls to the admin backend use campaign-derived authentication.

## Lifecycle

The public FastAPI application owns WebSocket manager startup and shutdown.
Use exposed lifecycle state rather than inspecting private task objects.

Remote title and favicon metadata retrieval is asynchronous, bounded,
SSRF-protected, cached, and single-flight. Keep blocking network operations off
the event loop.
