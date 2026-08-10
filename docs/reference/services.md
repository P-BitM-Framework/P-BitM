# Services

## Compose services

| Service | Role | Published ports |
|---|---|---|
| `frontend` | HTTPS dashboard and admin API proxy | `127.0.0.1:8443` |
| `backend` | Admin control plane | none; private `8443` |
| `traefik` | Public campaign router and TLS | `80`, `443` |
| `traefik-docker-proxy` | Read-only Docker discovery subset | none |
| `docker-proxy` | Privileged, network-restricted admin Docker operations | none |
| `mailhog` | Development SMTP sink | `1025`, `8025` in development |

Frontend waits for the backend healthcheck. Frontend, backend, Traefik, and
socket proxies use `restart: unless-stopped`.

`docker-proxy` can mutate Docker state through its enabled API operations and
must be treated as a privileged control-plane service. Its port is available
only on the internal `docker-control` network. `traefik-docker-proxy` is a
separate discovery subset with mutation methods disabled.

## Dynamic workloads

| Workload | Image default | Owner |
|---|---|---|
| Campaign service | `p-bitm:latest` | Admin backend |
| Campaign egress | `p-bitm-egress:latest` | Admin backend |
| VNC session | `bitm-vnc:latest` | Admin backend |
| Selkies session | `bitm-selkies:latest` | Admin backend |

Dynamic workloads are not Compose services and are not guaranteed to stop when
the base Compose project is brought down.

## Healthchecks

- Frontend checks local HTTPS with certificate verification disabled only for
  the container-local probe.
- Backend checks `http://127.0.0.1:8443/health`.
- Traefik uses its built-in ping healthcheck.
