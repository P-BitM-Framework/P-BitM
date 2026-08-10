# Networking and TLS

## Dashboard

The frontend publishes `127.0.0.1:8443` and serves HTTPS. Keep this loopback
binding unless a separately reviewed administrative access layer protects it.
Frontend nginx proxies API traffic to the backend on the private dashboard
network.

## Campaign traffic

Traefik publishes ports 80 and 443. In production, each campaign uses an
approved hostname and Traefik obtains certificates through the configured DNS
challenge. In development, routing uses the generated local configuration and
self-signed certificates.

The optional webcam feature additionally requires outbound DNS and UDP access
to Google's public STUN service on port `19302` from both the participant-side
browser environment and the operator's dashboard browser. Webcam media uses a
direct WebRTC path when ICE negotiation succeeds; there is no configured TURN
relay fallback.

## Docker networks

- `bitm-dashboard` connects frontend and admin backend.
- `bitm-network` connects control-plane and campaign routing components.
- `docker-control` is an internal network for admin Docker operations.
- `traefik-control` is an internal network for Traefik discovery.
- Additional campaign networks are created dynamically for isolation.

## Forwarded client addresses

Only headers from explicitly trusted proxy paths are accepted when resolving
client addresses. Do not add arbitrary public proxy hosts to
`TRUSTED_DASHBOARD_PROXY_HOSTS`.

## Certificates

`setup` creates local certificate files when missing. The private key remains
host-readable for the physical-machine operator and is copied into the
frontend image with runtime ownership and restrictive mode. Do not loosen the
host key mode to solve container startup problems; rebuild through the CLI so
the Dockerfile applies the correct in-image ownership.
