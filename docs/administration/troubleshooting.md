# Troubleshooting

## Docker reports that the legacy builder is deprecated

P-BitM requires BuildKit through the Docker Buildx plugin. The warning, or an
error such as `the --chmod option requires BuildKit`, means the Docker CLI is
falling back to the unsupported legacy builder.

Package names depend on the installed Docker distribution. For Ubuntu's
`docker.io` package:

```bash
sudo apt-get update
sudo apt-get install docker-buildx docker-compose-v2
```

If APT cannot locate these Ubuntu packages, verify that the `universe`
component is present in the configured Ubuntu sources.

For `docker-ce`, configure
[Docker's official Ubuntu repository](https://docs.docker.com/engine/install/ubuntu/)
and install:

```bash
sudo apt-get update
sudo apt-get install docker-buildx-plugin docker-compose-plugin
```

Do not mix the two package families. In both cases, verify:

```bash
docker buildx version
docker compose version
```

No environment export is needed after the plugins are installed. Setting
`DOCKER_BUILDKIT=1` does not install or replace a missing Buildx component; if
Buildx is absent, it turns the fallback warning into a build error.
`COMPOSE_DOCKER_CLI_BUILD` has no effect in Compose v2. Do not set
`DOCKER_BUILDKIT=0`, because that explicitly selects the legacy builder.

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
