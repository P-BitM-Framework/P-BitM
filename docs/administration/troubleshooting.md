# Troubleshooting

## The CLI cannot import `rich`

Activate the project virtual environment and install root dependencies:

```bash
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Storage directories are missing

Run setup instead of creating ad-hoc container-only paths:

```bash
python3 p-bitm.py setup
python3 p-bitm.py doctor
```

Setup recreates `storage/` and `storage/campaigns/` with host-accessible
modes. Runtime logs are available through Docker and the CLI rather than as
duplicated files under storage.

## Frontend cannot read `key.pem`

Do not make the host key world-readable. Run:

```bash
python3 p-bitm.py up --build
```

The frontend Dockerfile copies the key with ownership for its unprivileged
nginx user.

## A service is unhealthy

```bash
python3 p-bitm.py status
docker compose -f server/docker-compose.yml ps
docker compose -f server/docker-compose.yml logs frontend backend traefik
```

Frontend startup waits for the backend healthcheck. Fix the first unhealthy
dependency rather than repeatedly restarting the full stack.

## Browser session is blank or slow

Check campaign and participant status, then inspect logs:

```bash
python3 p-bitm.py campaign <campaign-id> logs --tail 200
python3 p-bitm.py campaign <campaign-id> victim <victim-id> logs --tail 200
```

Confirm that the selected browser image exists, the target URL is reachable
through the campaign egress path, and the readiness timeout has not expired.

## Port conflict

The dashboard requires loopback port `8443`; Traefik requires public ports 80
and 443. Identify the existing listener and resolve the conflict deliberately.
Do not change published ports without also reviewing dashboard URLs, routing,
firewall rules, and documentation.

## Database warning

Stop writes, create a complete storage backup, and run `doctor`. Do not delete
the database as an initial repair step.
