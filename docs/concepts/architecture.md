# Architecture

P-BitM separates the trusted administrative control plane from per-campaign
and per-session workloads.

```text
                         ADMINISTRATIVE CONTROL PLANE

  Operator browser
         |
         | HTTPS on the loopback interface
         v
  Frontend nginx  ------ authenticated API ------>  Admin backend
                                                        |       |
                                                        |       +--> SQLite
                                                        |            and storage
                                                        |
                                                        +--> Restricted Docker proxy
                                                                  |
                                                                  v
                                                             Docker Engine
                                                                  |
                           provisions and manages                 |
                           campaign services and   <--------------+
                           browser containers


                           CAMPAIGN AND BROWSER PLANE

  Victim browser
         |
         | HTTPS and WebSocket
         v
      Traefik
         |
         v
  Per-campaign service  <---- authenticated internal API ---->  Send Data to Admin backend
         |
         | private, victim-scoped route
         v
  Assigned Selkies or VNC browser container
```

In this documentation, **victim** means the authorized assessment target whose
browser opens a campaign link. P-BitM must only be used with explicit written
authorization.

## Control plane

The Vue frontend serves the dashboard and proxies authenticated API requests
to the FastAPI admin backend. The admin backend owns users, resources,
campaign state, storage, and Docker orchestration.

## Campaign plane

Each campaign runs a dedicated FastAPI/nginx service behind Traefik. It handles
the campaign entry flow, victim WebSockets, authenticated communication with
the admin backend, and private routing to the assigned browser container.

## Browser plane

Each active victim receives an isolated VNC or Selkies container. Browser
containers do not receive direct access to the Docker socket or admin
credentials.

## Docker mediation

Traefik and the admin backend use separate socket-proxy services and internal
networks. Traefik receives read-only discovery capabilities. The admin backend
receives the limited mutation capabilities required to manage application
workloads.
