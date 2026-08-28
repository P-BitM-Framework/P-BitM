# Persistent Browser-In-The-Middle

<p align="center">
  <img src="assets/readme/p-bitm-logo.png" alt="P-BitM Logo" width="220">
</p>

<p align="center">
  <a href="https://github.com/P-BitM-Framework/P-BitM/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/P-BitM-Framework/P-BitM/ci.yml?branch=main&label=CI" alt="CI status"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0--only-blue.svg" alt="License: GPL-3.0-only"></a>
  <a href="config.yaml"><img src="https://img.shields.io/badge/version-0.1.0-blue.svg" alt="Version 0.1.0"></a>
  <a href="https://github.com/P-BitM-Framework/P-BitM/stargazers"><img src="https://img.shields.io/github/stars/P-BitM-Framework/P-BitM?style=flat" alt="GitHub stars"></a>
  <a href="https://p-bitm-2269ecee.mintlify.site"><img src="https://img.shields.io/badge/documentation-P--BitM%20Docs-C4472D" alt="P-BitM documentation"></a>
</p>

P-BitM is a containerized platform for controlled browser-in-the-middle
security assessments. It combines an administrative dashboard, isolated
campaign services, dedicated browser containers, live session viewing, and
bounded evidence collection.

> [!CAUTION]
> Use P-BitM only on systems you own or where you have explicit written authorization.
> Read the [authorized-use policy](docs/security/authorized-use.md).

<p align="center">
  <img src="assets/readme/victim-dashboard.png" alt="P-BitM victim dashboard with demo data, live control, and evidence panels" width="1000">
</p>

> [!IMPORTANT]
> P-BitM is under active development. Its modular architecture is designed to
> grow with community feedback and contributions, especially new ideas for
> client-side modules and Firefox extensions used in authorized assessments.

## Highlights

- Red Team Operator Dashboard
- Campaign and victim containers lifecycle management
- Target, email, SMTP, landing-page, plugin, and module libraries
- Immediate and scheduled campaigns
- VNC and Selkies browser-session modes
- Role-based administrative access
- Restricted Docker socket proxies and isolated campaign networks
- Campaign and per-session exports

## Product demos

The short recordings below show P-BitM in a controlled, authorized environment.
Open the linked documentation pages for context and the complete video catalog.

<table>
  <tr>
    <td align="center" width="50%">
      <a href="https://p-bitm-2269ecee.mintlify.site/user-guide/campaigns#campaign-creation-demo">
        <img src="assets/readme/campaign-creation-demo.jpg" alt="Thumbnail from the controlled campaign creation demo" width="100%">
      </a>
      <br>
      <a href="https://p-bitm-2269ecee.mintlify.site/user-guide/campaigns#campaign-creation-demo">Watch the campaign creation demo</a>
    </td>
    <td align="center" width="50%">
      <a href="https://p-bitm-2269ecee.mintlify.site/user-guide/plugins#file-interception-demo">
        <img src="assets/readme/file-hijacking-demo.jpg" alt="Thumbnail from the controlled file interception demo" width="100%">
      </a>
      <br>
      <a href="https://p-bitm-2269ecee.mintlify.site/user-guide/plugins#file-interception-demo">Watch the file interception demo</a>
    </td>
  </tr>
</table>

## Quick start

Requirements: Python 3.9+, Docker Engine 23.0+, Docker Buildx and Compose
plugins, Git, and OpenSSL. The standalone `docker-compose` command is not
supported. On Linux, the current user should normally have direct access to
Docker; P-BitM automatically aligns its unprivileged containers with the
selected host UID/GID when bind-mounted storage is used.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 p-bitm.py setup
python3 p-bitm.py doctor
python3 p-bitm.py up
```

The dashboard defaults to `https://127.0.0.1:8443/`. Review `config.yaml`
before setup, especially the environment and production DNS challenge.

## Architecture and codebase

P-BitM separates the trusted administrative control plane from the
campaign-facing services and browser sessions. The dashboard talks to the
admin backend, which stores persistent state and provisions isolated workloads
through a restricted Docker socket proxy. Public campaign traffic is routed by
Traefik to a per-campaign service, which validates the victim session and
connects it to its assigned browser container.

```text
Operator browser
  -> Frontend nginx
  -> Admin backend
     -> SQLite and storage
     -> Restricted Docker proxy
        -> Per-campaign services
        -> Per-session VNC or Selkies browser containers

Victim browser
  -> Traefik
  -> Per-campaign service
  -> Assigned browser session
```

The source tree is organized around those boundaries:

```text
.
├── bitm-images/
│   ├── common/              # Shared browser-runtime files
│   ├── selkies/             # Selkies browser runtime
│   └── vnc/                 # VNC/noVNC browser runtime
├── assets/                  # Project and README visual assets
├── cli/                     # CLI implementation
├── docs/                    # Credits, use policy, and docs link
├── modules/                 # Built-in modules
├── server/
│   ├── backend/             # Administrative control plane
│   ├── backend-phishing/    # Per-campaign service
│   ├── egress-proxy/        # Controlled campaign egress
│   ├── frontend/            # Administrative dashboard
│   └── traefik/             # Public routing and TLS
└── tests/                   # Shared regression tests
```

The main codebase boundaries are:

| Path | Responsibility |
| --- | --- |
| `p-bitm.py`, `cli/` | CLI entry point, configuration, setup, diagnostics, and lifecycle operations |
| `server/frontend/` | Vue administrative dashboard and its nginx entry point |
| `server/backend/` | Trusted FastAPI control plane, persistence, authentication, and container orchestration |
| `server/backend-phishing/app/` | Per-campaign FastAPI service, public routes, tracking, and session admission |
| `server/traefik/` | Public routing and TLS configuration |
| `server/egress-proxy/` | Controlled outbound proxy used by campaign workloads |
| `bitm-images/common/` | Files shared by the browser runtimes, including policies, extensions, and keylogging support |
| `bitm-images/vnc/` | VNC/noVNC browser runtime |
| `bitm-images/selkies/` | Selkies browser runtime using H.264 over WebSockets |
| `modules/` | Built-in modules that can be seeded into the application |
| `tests/` | CLI and shared regression tests; service-specific tests live beside their services |
| `assets/` | Project and README visual assets |
| `docs/` | Credits, authorized-use policy, and link to published docs |

For a deeper walkthrough, read the
[architecture](https://p-bitm-2269ecee.mintlify.site/concepts/architecture),
[request flow](https://p-bitm-2269ecee.mintlify.site/concepts/request-flow), and
[service reference](https://p-bitm-2269ecee.mintlify.site/reference/services).
Contributors should start with the
[development setup](https://p-bitm-2269ecee.mintlify.site/development/setup).

## Documentation

The complete, current documentation is published at
[P-BitM Docs](https://p-bitm-2269ecee.mintlify.site).

- [Installation](https://p-bitm-2269ecee.mintlify.site/getting-started/installation)
- [Quick start](https://p-bitm-2269ecee.mintlify.site/getting-started/quick-start)
- [Video demos](https://p-bitm-2269ecee.mintlify.site/video-demos)
- [Architecture](https://p-bitm-2269ecee.mintlify.site/concepts/architecture)
- [Deployment](https://p-bitm-2269ecee.mintlify.site/administration/deployment)
- [CLI reference](https://p-bitm-2269ecee.mintlify.site/reference/cli)
- [Security model](https://p-bitm-2269ecee.mintlify.site/concepts/security-model)
- [Authorized-use policy](docs/security/authorized-use.md)

## Development

```bash
python3 -m pip install pytest
python3 -m pytest tests
PYTHONPATH=server/backend python3 -m pytest server/backend/tests
PYTHONPATH=server/backend-phishing/app python3 -m pytest server/backend-phishing/tests
(cd server/frontend && npm ci && npm run lint && npm test && npm run build)
python3 scripts/release_checks.py
```

See the
[development guide](https://p-bitm-2269ecee.mintlify.site/development/setup).
Contributions are welcome; read [`CONTRIBUTING.md`](CONTRIBUTING.md) before
opening a pull request.

## Security

Read [`SECURITY.md`](SECURITY.md) before reporting a vulnerability. Do not
include real credentials, collected data, tracking identifiers, or personal
information in public reports.

## License

P-BitM's original code is distributed under the
[GNU General Public License version 3 only](LICENSE) (`GPL-3.0-only`).
Third-party components remain subject to their respective licenses; see
[Third-Party Notices](THIRD_PARTY_NOTICES.md) and
[Credits and acknowledgements](docs/CREDITS.md).
