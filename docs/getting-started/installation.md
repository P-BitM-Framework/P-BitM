# Installation

## 1. Obtain the source

```bash
git clone https://github.com/P-BitM-Framework/P-BitM
cd P-BitM
```

## 2. Verify the Docker toolchain

P-BitM requires Docker Engine 23.0 or newer plus the Buildx and Compose
plugins. All three commands must succeed:

```bash
docker version --format '{{.Server.Version}}'
docker buildx version
docker compose version
```

The standalone `docker-compose` command is not supported. See the
[requirements](requirements.md) for installation guidance.

## 3. Install the CLI dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## 4. Review the configuration

Open `config.yaml` and confirm at least:

- `app.environment`;
- `app.dashboard_url`;
- storage and certificate paths;
- enabled Docker images;
- DNS challenge provider and credential variable names.

Do not place DNS credentials or application secrets in `config.yaml`.

## 5. Provision runtime files

```bash
python3 p-bitm.py setup
```

Setup checks Docker Engine, Buildx, and the Compose plugin; generates
`server/.env`; provisions DNS credential files for production; creates storage
directories; and generates local TLS certificates when they are missing.

DNS credentials are stored below the ignored `server/.secrets/dns/` directory
with restrictive permissions. To replace them later:

```bash
python3 p-bitm.py setup --rotate-dns-secrets
```

## 6. Run diagnostics

```bash
python3 p-bitm.py doctor
```

Resolve every failure before starting the stack. Warnings are non-blocking
during normal operation but block `doctor --strict`.

Continue with the [quick start](quick-start.md).
