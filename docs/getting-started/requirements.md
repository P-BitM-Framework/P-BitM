# Requirements

## Host

- Linux host recommended for production deployments.
- Python 3.9 or newer for the host CLI.
- Docker Engine 23.0 or newer with a running daemon. Use a currently supported
  release for production.
- Docker Buildx plugin, exposed as `docker buildx`.
- Docker Compose plugin, exposed as `docker compose`.
- Git and OpenSSL.
- Enough disk space for browser images, campaign artifacts, and exports.

The standalone `docker-compose` command and Docker's legacy image builder are
not supported. P-BitM uses BuildKit features and checks the complete Docker
toolchain before setup and startup.

Docker Desktop includes Buildx and Compose. Linux package names depend on how
Docker Engine was installed. Do not mix Ubuntu's Docker packages with Docker
CE packages from Docker's repository.

### Ubuntu packages

If the host uses Ubuntu's `docker.io` package, install Ubuntu's plugin
packages:

```bash
sudo apt-get update
sudo apt-get install docker-buildx docker-compose-v2
```

These packages are distributed through Ubuntu's `universe` component, which
is normally already enabled. If APT cannot locate them, check that component
in the host's configured Ubuntu sources.

### Docker CE packages

If the host uses `docker-ce`, first configure
[Docker's official Ubuntu repository](https://docs.docker.com/engine/install/ubuntu/),
then install its plugin packages:

```bash
sudo apt-get update
sudo apt-get install docker-buildx-plugin docker-compose-plugin
```

For a new production host, the Docker CE installation documented by Docker is
recommended. Whichever package family is selected, verify the resulting CLI:

```bash
docker version --format '{{.Server.Version}}'
docker buildx version
docker compose version
```

No BuildKit environment variables are required. A supported Engine uses
BuildKit by default, and P-BitM invokes Buildx explicitly for custom images.
`COMPOSE_DOCKER_CLI_BUILD` is unsupported by Compose v2.

The CLI supports `amd64` and `arm64` image selection. Actual browser streaming
support still depends on the host, container runtime, and selected image.

## Python dependencies

Install the root CLI dependencies from `requirements.txt`. A virtual
environment is recommended:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

Running the backend source or its test suites directly outside Docker requires
Python 3.10 or newer. The application containers use their own supported
Python runtime, independently of the host CLI version.

## Network and DNS

The dashboard listens on `https://127.0.0.1:8443/` by default. Production
campaigns require:

- inbound TCP ports 80 and 443;
- DNS records resolving campaign hostnames to the deployment host;
- credentials for the DNS challenge provider configured in `config.yaml`.

Keep the administrative dashboard on loopback or behind a separately secured
administrative access layer.

## Authorization

Before deployment, define the approved targets, dates, operators, collection
scope, data retention, and emergency stop procedure in writing.
