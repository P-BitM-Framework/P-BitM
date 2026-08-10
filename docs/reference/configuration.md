# Configuration reference

`config.yaml` is the operator-managed configuration source.

## Application and paths

- `app.name`, `app.version`, `app.dashboard_url`
- `app.environment`: `development` or `production`
- `paths.docker_compose` and `paths.docker_compose_dev`
- generated environment, DNS secret, Traefik, storage, log, campaign, and
  certificate paths

Relative paths resolve from the repository root.

## Docker

`docker.images` defines the tag, build context, Dockerfile, enabled state, and
architecture-specific Selkies Dockerfiles. `docker.compose_images` lists
images built by Compose. `docker.socket` and `docker.timeout` configure host
tooling.

## TLS and DNS

`ssl.auto_generate` controls local certificate provisioning. Certificate
identity fields and `validity_days` apply to generated local certificates.

`ssl.dns_challenge` contains:

- `provider`: Traefik/lego provider name;
- `credentials`: required secret variable names;
- `environment`: non-secret provider variables.

Credential values must not be stored in this file.

## Administration and sessions

`admin` defines the bootstrap username/email and admin session limits.
`sessions` defines active-session capacity, token TTL, startup/handshake
timeouts, and admission rate limits.

## Networks, cleanup, and CLI

`network` controls IP detection and named Docker networks. `containers`
defines application naming patterns. `cleanup` defines policy defaults.
`cli.confirm_destructive` controls confirmation prompts; keep it enabled for
interactive deployments.

Run `python3 p-bitm.py setup` after changing values that generate runtime
state.
