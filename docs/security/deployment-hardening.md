# Deployment hardening

## Control plane

- Keep `127.0.0.1:8443` bound to loopback.
- Use a secured administrative tunnel or access layer for remote operators.
- Change the initial administrator password immediately.
- Assign the `operator` role unless administrator privileges are required.
- Keep session TTL and concurrent-session limits bounded.

## Secrets

- Generate runtime secrets through `setup`.
- Keep `server/.env`, DNS secret files, certificates, and storage untracked.
- Do not pass passwords as CLI arguments.
- Rotate SMTP and DNS credentials after the engagement.
- Back up encryption keys together with encrypted data that must be retained.

## Containers and network

- Preserve separate Docker socket proxies and internal control networks.
- Treat the admin Docker proxy as privileged even though the host socket is
  mounted read-only; enabled Docker API methods can still mutate host state.
- Never publish either Docker proxy port or connect untrusted workloads to
  `docker-control` or `traefik-control`.
- Do not mount the Docker socket into campaign or browser containers.
- Keep `no-new-privileges` and dropped capabilities on control-plane services.
- Restrict public firewall rules to required campaign ports.
- Review remote targets and egress requirements before launch.

## Content

Treat landing pages, plugins, modules, imported ZIP files, templates, and
exports as untrusted until reviewed. Apply engagement-specific code review,
malware scanning, evidence encryption, and retention controls.

## Release gate

Run:

```bash
python3 p-bitm.py doctor --strict --format json
```

Store the report with the tested commit and resolve every warning and failure.
