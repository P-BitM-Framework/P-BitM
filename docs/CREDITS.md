# Credits and acknowledgements

P-BitM builds on open-source projects and ideas shared by the security
community. This page credits projects whose code is incorporated or adapted,
as well as projects that influenced P-BitM without supplying code.

The canonical legal inventory is `THIRD_PARTY_NOTICES.md` at the repository
root. Package-manager dependencies are not repeated here unless they also
materially influenced P-BitM's design.

## Code, components, and project lineage

### Selkies

- **Repository:** [selkies-project/selkies](https://github.com/selkies-project/selkies)
- **Relationship:** incorporated and adapted code
- **Influence:** browser streaming dashboard, web core, input handling,
  controller, and related frontend assets
- **Active path:** `bitm-images/selkies/`
- **Upstream license:** `MPL-2.0`

The active Docker build fetches the upstream source and compiles its
dashboard. P-BitM's `selkies-core.js` is adapted primarily from upstream
`addons/selkies-web-core/selkies-ws-core.js` and is installed at the web-core
entry point before compilation. Selected upstream controller, nginx, and
`jsdb` assets are also carried into the built dashboard. P-BitM preserves the
upstream license on files containing Selkies code.

### LinuxServer.io Selkies base image

- **Repository:** [linuxserver/docker-baseimage-selkies](https://github.com/linuxserver/docker-baseimage-selkies)
- **Relationship:** incorporated runtime base
- **Influence:** container framework, desktop and streaming runtime, system
  layout, and stock Selkies services
- **Relevant path:** the active multi-arch Selkies `Dockerfile`
- **Upstream license:** `GPL-3.0-only`

The active image adds P-BitM files and replaces the stock dashboard. Its
frontend build stage separately uses LinuxServer's generic Alpine base image
as a build environment.

### noVNC

- **Repository:** [novnc/noVNC](https://github.com/novnc/noVNC)
- **Relationship:** incorporated and adapted during image build
- **Influence:** VNC browser-session client
- **Relevant path:** `bitm-images/vnc/Dockerfile`
- **Upstream licenses:** primarily `MPL-2.0`, with per-file licenses recorded
  in noVNC's `LICENSE.txt`

The VNC build uses noVNC and applies explicit changes to its MPL-2.0 core
library during the Docker build. The complete clone also contains HTML, CSS,
fonts, images, and incorporated libraries under the BSD-2-Clause, OFL-1.1,
CC BY-SA 3.0, MIT, and other BSD-style terms recorded upstream. P-BitM's own
entry page is separate from those upstream assets.

### EvilnoVNC

- **Repository:** [JoelGMSec/EvilnoVNC](https://github.com/JoelGMSec/EvilnoVNC)
- **Relationship:** modified and adapted code
- **Author credited upstream:** Joel Gámez Molina (`@JoelGMSec`)
- **Influence:** VNC session-container architecture, browser/noVNC workflow,
  startup orchestration, and noVNC tuning
- **Relevant path:** `bitm-images/vnc/`
- **Upstream license:** GNU General Public License version 3

P-BitM's VNC implementation evolved from EvilnoVNC and was subsequently
reworked around Firefox, campaign-specific routing, extensions, keylogging, a
local proxy, and supervised services. EvilnoVNC itself uses noVNC, so both
projects are credited separately.

### Peeko

- **Repository:** [b3rito/peeko](https://github.com/b3rito/peeko)
- **Relationship:** modified and adapted code
- **Authors credited upstream:** b3rito at mes3hacklab and GioPpeTto
- **Influence:** browser WebSocket agent and its command/response flow
- **Relevant path:** `server/backend-phishing/app/static/index.js`
- **Upstream license:** GNU General Public License version 3

P-BitM's agent started from Peeko's browser agent and was adapted with
platform-specific behavior, including routing, authenticated sessions,
message handling, modules, data collection, and WebRTC features. The resulting
file remains credited to the upstream project and its authors.

## Inspiration and acknowledgements

### CuddlePhish

- **Repository:** [fkasler/cuddlephish](https://github.com/fkasler/cuddlephish)
- **Relationship:** design inspiration; no code copied
- **Influence:** early reference for using WebRTC rather than VNC to deliver
  an interactive browser stream in a weaponized BitM workflow
- **Upstream license:** MIT

CuddlePhish demonstrated a multi-user BitM design in which WebRTC carries the
browser video while WebSockets handle pairing, signaling, and input. It
influenced P-BitM's exploration of browser-streaming alternatives to VNC.
P-BitM does not reuse CuddlePhish code, and its current Selkies integration is
configured in WebSocket mode rather than using CuddlePhish's WebRTC
implementation.

### Gophish

- **Repository:** [gophish/gophish](https://github.com/gophish/gophish)
- **Relationship:** design and workflow inspiration; no code copied
- **Original author credited upstream:** Jordan Wright
- **Influence:** operator-facing style and the creation, organization, and
  tracking of traditional phishing campaigns
- **Upstream license:** MIT

Gophish influenced the way P-BitM presents familiar phishing concepts such as
target lists, SMTP profiles, email templates, landing pages, campaign
lifecycle, and tracking results. P-BitM implements its own code and extends
that operational model with DNS configuration, plugins, modules, and
per-victim BitM container and live-session management.

## Adding another project

Add a project when code, documentation, assets, configuration, or a material
workflow was copied, adapted, or used as a meaningful design reference.
Record:

1. the repository name and canonical URL;
2. whether code was incorporated, modified, adapted, or not copied;
3. the affected P-BitM paths or features;
4. the upstream version, when useful;
5. the upstream license.

Do not describe copied code as mere inspiration. Ordinary package-manager
dependencies do not need a credits entry unless they also materially
influenced P-BitM's design.
