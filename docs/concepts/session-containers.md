# Session containers

P-BitM creates one browser container for each active participant session.

## Images

- `bitm-vnc:latest` provides the VNC-based browser runtime.
- `bitm-selkies:latest` provides the Selkies streaming runtime selected for
  the host architecture.

The selected campaign protocol determines which image is used. Image names and
Dockerfiles are configured in `config.yaml`.

## Readiness

After creation, the admin backend waits for the container-specific readiness
signal up to `VICTIM_READY_TIMEOUT_SECONDS`. A container that exists but is not
ready is not presented as a usable live session.

## Identity and isolation

Containers and networks carry application labels. Management operations verify
campaign ID, participant ID, and role labels before executing or removing a
workload. Campaign networks isolate unrelated campaigns.

The participant's User-Agent is captured as session metadata before the
browser container is created. The optional outbound User-Agent behavior is
implemented by a built-in Firefox extension and is not a complete browser
fingerprint substitution. See [User-Agent override](../user-guide/plugins.md#user-agent-override)
for its compatibility limitations.

## Limits

Per-campaign admission and host-wide active-session limits protect runtime
capacity. Configure these according to measured host resources rather than
disabling them.
