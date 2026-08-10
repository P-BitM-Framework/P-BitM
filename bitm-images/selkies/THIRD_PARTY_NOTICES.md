# Third-Party Notices — bitm-images/selkies

This image is built on top of, and includes source derived from, the following
third-party projects. This project's own license is in the repository root
[`LICENSE`](../../LICENSE) (GPL-3.0-only); it does not change the license of
the third-party components listed below.

## linuxserver/docker-baseimage-selkies

- **License:** GPL-3.0-only
- **Source:** https://github.com/linuxserver/docker-baseimage-selkies
- **Used as:** the runtime base image
  (`ghcr.io/linuxserver/baseimage-selkies:debiantrixie`)

The runtime base supplies the LinuxServer container framework, desktop and
streaming runtime, system user/layout, and stock Selkies services. P-BitM adds
its own layers and replaces the stock dashboard.

The frontend build stage separately uses
`ghcr.io/linuxserver/baseimage-alpine:3.22` as its build environment.

## selkies-project/selkies

- **License:** MPL-2.0 (Mozilla Public License 2.0, full text: https://mozilla.org/MPL/2.0/)
- **Source:** https://github.com/selkies-project/selkies
- **Files vendored/derived in this repo:**
  - [`selkies/selkies-core.js`](selkies/selkies-core.js) — modified and
    adapted primarily from upstream
    `addons/selkies-web-core/selkies-ws-core.js`. The build installs it at
    `addons/selkies-web-core/selkies-core.js` before compiling the dashboard.
    It retains the original MPL-2.0 header.
  - `addons/universal-touch-gamepad/universalTouchGamepad.js` (upstream,
    unmodified) — copied at build time into the final image as
    `src/index-1337090834.js`. Renamed but not otherwise altered.

Under the MPL-2.0 larger-work provisions, files containing upstream Selkies
source remain under MPL-2.0 with their notices preserved and source available.

## Firefox ESR, nginx, openbox, and other Debian/Alpine packages

Installed via `apt`/`apk` from their respective upstream repositories,
unmodified. Each remains under its own upstream license; see the individual
package's Debian/Mozilla documentation for details.

P-BitM's original files remain under the repository's
[`LICENSE`](../../LICENSE). Files containing upstream Selkies source remain
under MPL-2.0, and the LinuxServer base retains its own license and notices.
