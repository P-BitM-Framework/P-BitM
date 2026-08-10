# Third-Party Notices

P-BitM's original code is licensed under the GNU General Public License
version 3 only (`GPL-3.0-only`). That license does not replace or remove the
licenses, copyright notices, or attribution requirements of third-party
material.

This document records third-party projects whose source is incorporated,
adapted, or modified by the P-BitM build. It is not a generated inventory of
every package installed through `apt`, `apk`, `pip`, or `npm`. Those packages
remain under the licenses published by their respective maintainers.

## Selkies

- **Project:** [selkies-project/selkies](https://github.com/selkies-project/selkies)
- **License:** Mozilla Public License 2.0 (`MPL-2.0`)
- **Relationship:** incorporated and adapted
- **Affected areas:** `bitm-images/selkies/`

The active Docker build fetches the upstream repository and compiles the
Selkies dashboard. P-BitM's `selkies-core.js` is adapted primarily from
upstream `addons/selkies-web-core/selkies-ws-core.js`; the build installs it
at `addons/selkies-web-core/selkies-core.js` before compilation and carries
selected upstream assets into the result. Files derived from Selkies remain
under the MPL-2.0, with their original copyright and license notices
preserved. The current image has additional file-level details in
[`bitm-images/selkies/THIRD_PARTY_NOTICES.md`](bitm-images/selkies/THIRD_PARTY_NOTICES.md).

## LinuxServer.io Selkies base image

- **Project:** [linuxserver/docker-baseimage-selkies](https://github.com/linuxserver/docker-baseimage-selkies)
- **License:** GNU General Public License version 3 only (`GPL-3.0-only`)
- **Relationship:** active runtime container base
- **Active build file:** `bitm-images/selkies/Dockerfile`

The base supplies the container framework, desktop and streaming runtime,
system layout, and stock Selkies services. P-BitM adds its own layers and
replaces the stock dashboard with the build produced from
`selkies-project/selkies`. P-BitM does not claim ownership of the upstream
base image or its contents.

The Selkies frontend build stage also uses
`ghcr.io/linuxserver/baseimage-alpine:3.22` as a generic build environment.

## noVNC

- **Project:** [novnc/noVNC](https://github.com/novnc/noVNC)
- **Version used by the build:** `v1.7.0`
- **Relationship:** modified and adapted during the VNC image build
- **Affected area:** `bitm-images/vnc/Dockerfile`

The build clones the noVNC source distribution and applies focused changes to
`core/rfb.js`. That core JavaScript remains under the Mozilla Public License
2.0 (`MPL-2.0`). The P-BitM-specific `bitm-images/vnc/conf/novnc.html` entry
page is not presented as upstream noVNC HTML.

The cloned noVNC distribution uses the file-level license matrix stated in
its upstream `LICENSE.txt`:

- core JavaScript, including `core/rfb.js` and `core/base64.js`: `MPL-2.0`;
- upstream `*.html` and `app/styles/*.css`: `BSD-2-Clause`;
- Orbitron fonts: `OFL-1.1`;
- upstream application images: `CC-BY-SA-3.0`;
- `vendor/pako/`: MIT;
- `core/des.js`: various BSD-style licenses;
- other files: the license header in the file, or the upstream default
  `MPL-2.0` where no more specific notice applies.

The upstream `LICENSE.txt`, `AUTHORS`, referenced license texts, copyright
headers, and third-party notices are retained in the cloned source included in
the image. P-BitM does not relicense those files.

## EvilnoVNC

- **Project:** [JoelGMSec/EvilnoVNC](https://github.com/JoelGMSec/EvilnoVNC)
- **License:** GNU General Public License version 3
- **Author credited upstream:** Joel Gámez Molina (`@JoelGMSec`)
- **Relationship:** modified and adapted code
- **Affected area:** `bitm-images/vnc/`

P-BitM's VNC container workflow evolved from EvilnoVNC, including its
container build, browser/noVNC integration, startup orchestration, and noVNC
quality and compression tuning. P-BitM subsequently modified and extended
that implementation for its Firefox-based session containers, campaign
routing, extensions, keylogging, local proxy, and service supervision. Credit
and copyright in the upstream implementation remain with the EvilnoVNC author
and contributors.

## Peeko

- **Project:** [b3rito/peeko](https://github.com/b3rito/peeko)
- **License:** GNU General Public License version 3
- **Authors credited upstream:** b3rito at mes3hacklab and GioPpeTto
- **Relationship:** modified and adapted code
- **Affected file:** `server/backend-phishing/app/static/index.js`

P-BitM's browser WebSocket agent was based on Peeko's `static/agent.js` and
subsequently modified with P-BitM-specific behavior, including routing,
session authorization, messaging, modules, data collection, and WebRTC
integration. Credit and copyright in the upstream implementation remain with
the Peeko authors.

## Package-managed dependencies

Python and JavaScript dependencies are declared in the repository's
requirements, constraints, lockfiles, and package manifests. Container system
packages are declared by the Dockerfiles. Each dependency retains its upstream
license. A dependency being compatible with P-BitM does not make it
`GPL-3.0-only`.

## Corrections

If an upstream project, relationship, copyright notice, or license is missing
or described incorrectly, report it using the contact information in
[`SECURITY.md`](SECURITY.md). Attribution corrections do not need to contain
security-sensitive details.
