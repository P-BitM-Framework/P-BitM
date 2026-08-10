# Overview

P-BitM coordinates authorized browser-based assessment campaigns from a local
administrative control plane. Each campaign receives an isolated public
service, and each active participant receives a dedicated browser container.

## What the platform provides

- A Vue administrative dashboard.
- Campaign, target, template, SMTP, landing-page, plugin, and module libraries.
- Scheduled and immediate campaign lifecycle management.
- Isolated VNC or Selkies browser sessions.
- Event, keylog, screenshot, file, and module-result views.
- Campaign and per-session exports.
- A CLI for setup, diagnostics, lifecycle operations, and local administration.

## Trust boundary

The dashboard and admin backend are the trusted control plane. Campaign
services are isolated workloads exposed through Traefik. Browser containers
communicate with their campaign service and are managed by the admin backend
through a restricted Docker socket proxy.

P-BitM is designed for a single trusted host. It is not a multi-tenant hosted
service and should not be exposed as an unattended public control plane.

## Next step

Read the [requirements](requirements.md), then follow
[installation](installation.md).
