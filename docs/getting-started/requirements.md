# Requirements

## Host

- Linux host recommended for production deployments.
- Python 3.9 or newer for the host CLI.
- Docker Engine with a running daemon.
- Docker Compose plugin or the legacy `docker-compose` executable.
- Git and OpenSSL.
- Enough disk space for browser images, campaign artifacts, and exports.

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
