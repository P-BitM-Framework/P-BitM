# Security model

## Intended deployment

P-BitM assumes a single trusted host and a small set of authorized operators.
The dashboard is bound to loopback by default. Campaign services may be public,
but the control plane should not be directly exposed to the internet.

## Authentication

Administrator sessions are server-side and revocable. Browsers receive opaque
`Secure`, `HttpOnly`, `SameSite=Strict` cookies. Roles separate administrators
from operators.

Campaign-to-admin requests use per-campaign derived credentials. Public
session admission uses short-lived signed tokens, rate limits, handshake
timeouts, and capacity limits.

## Container control

No application service mounts an unrestricted writable Docker socket. Separate
socket proxies provide only the operations required by Traefik discovery and
admin orchestration.

The admin `docker-proxy` is nevertheless a privileged control-plane component:
its permitted Docker API operations include container lifecycle, network,
volume, image, and exec actions. Mounting the socket read-only protects the
socket file itself; it does not make enabled Docker API mutations read-only.
The proxy is therefore isolated on `docker-control` and must never be exposed
outside that internal network. The Traefik proxy has a separate discovery-only
policy with mutation methods disabled.

Compromise of the admin backend or its Docker proxy can affect dynamic
workloads and may affect the host. Movement from a campaign or victim workload
to this boundary is considered a security vulnerability.

## Input and egress controls

URLs, hostnames, uploads, WebSocket messages, archives, and stored paths are
validated and bounded. Remote metadata retrieval applies SSRF protections and
bounded reads. Campaign traffic uses isolated Docker networks and the
configured egress proxy.

## Client-side code transparency and detectability

P-BitM distributes its client-side JavaScript in readable, unobfuscated form.
This is intentional and supports source review, reproducibility, defensive
analysis, and authorized customization.

As a consequence, filenames, strings, routes, request patterns, and other
artifacts may act as stable indicators of compromise. P-BitM is not designed
to provide stealth or to evade security controls. Any modification must remain
within the written authorization and rules of engagement of the assessment.
Obfuscation must not be treated as a security control.

## Webcam WebRTC networking

Webcam streaming is started only by an explicit operator action and uses
peer-to-peer WebRTC with `stun.l.google.com:19302` and
`stun1.l.google.com:19302`. These public Google STUN endpoints are intentional
outbound network dependencies; the current deployment has no TURN relay.

The victim browser container and the dashboard browser contact Google STUN
separately, so Google can observe their public source addresses as independent
STUN clients. Monitoring on the participant side can observe STUN traffic to
Google. When direct ICE negotiation succeeds, webcam media travels over UDP to
the dashboard's public address. That address may be the same address already
associated with the campaign domain. Restrictive NAT or firewall rules can
prevent the direct connection from succeeding.

## Residual risk

Browser extensions, modules, landing-page HTML, SMTP credentials, collected
data, and exported profiles remain high-risk content. Technical controls do
not replace code review, scope approval, operator access control, monitoring,
or data-retention procedures.
