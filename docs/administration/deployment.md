# Deployment

## Select an environment

Set `app.environment` in `config.yaml`:

- `development` selects `server/docker-compose-dev.yml`, local TLS, path-based
  campaign routing, and MailHog;
- `production` selects `server/docker-compose.yml`, per-campaign hostnames, and
  the configured Traefik DNS challenge.

Run setup after changing the environment:

```bash
python3 p-bitm.py setup
python3 p-bitm.py doctor
```

## Build and start

```bash
python3 p-bitm.py up --build
```

The CLI builds the configured VNC, Selkies, campaign, and egress images, then
starts the Compose control-plane services. Later starts can omit `--build`
unless source or dependencies changed.

## Production checklist

- Keep the dashboard bound to loopback.
- Permit public inbound traffic only on ports 80 and 443.
- Point approved campaign hostnames to the deployment host.
- Configure DNS provider credential names in `config.yaml`.
- Store provider values through `setup`, not in tracked files.
- Run `doctor --strict` before an engagement.
- Confirm backup, retention, monitoring, and emergency-stop procedures.

## Stop

Run the global shutdown command:

```bash
python3 p-bitm.py down
```

`down` is terminal for the current runtime. It stops the control plane,
force-removes every app-owned campaign, participant, and campaign-egress
container, removes campaign networks, and marks active, paused, or scheduled
campaigns as completed. A later `up` does not resume them.

If any dynamic campaign resource cannot be removed, the command exits
unsuccessfully and leaves campaign state unchanged so an operator is not given
a false completed status. Resolve the reported Docker error and run `down`
again.
