# Live sessions

The victim detail view exposes live browser controls only after an authorized
participant has established a campaign session.

## Protocols

- **VNC** uses the VNC browser image and a proxied live view.
- **Selkies** uses the Selkies image and exposes additional streaming-quality
  settings in the campaign wizard.

Availability depends on the selected image, host architecture, browser
support, and network path. Do not add undocumented environment switches to
change the transport.

## Session behavior

Each active participant receives a dedicated browser container. The admin
backend validates campaign and victim ownership before returning stream access
or performing runtime actions.

If a stream does not become ready within the configured startup timeout, check
the campaign and victim logs before recreating the session.

## Screenshots

Screenshots are captured only when an authenticated operator requests one.
They are taken inside the browser container, validated, stored in the standard
campaign storage, and then shown in the victim gallery.
