# Request flow

## Administrative requests

1. The operator opens the loopback dashboard over HTTPS.
2. Frontend nginx proxies `/api` requests to the admin backend.
3. The backend authenticates the opaque server-side session cookie.
4. Route-level authorization checks the user role and resource ownership.
5. The backend reads or updates SQLite and campaign storage.

## Campaign admission

1. An approved recipient opens the campaign URL through Traefik.
2. The campaign service validates routing and tracking state.
3. The landing flow exchanges valid state for a short-lived signed session
   token.
4. The WebSocket handshake must complete within the configured timeout and
   admission limits.
5. The campaign service asks the authenticated admin backend to create the
   participant browser container.

Tracking identifiers and stream paths are bearer-like capabilities and must
not be written to routine logs or documentation examples.

## Collection

Campaign-local clients send bounded, validated records to private collection
routes. The campaign service forwards authenticated events to the admin
backend, which owns persistence. The dashboard later reads those records
through its authenticated API.
