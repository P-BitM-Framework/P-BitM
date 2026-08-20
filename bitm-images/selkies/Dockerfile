# syntax=docker/dockerfile:1
# The base images are multi-arch manifests; Docker selects amd64 or arm64.
FROM ghcr.io/linuxserver/baseimage-alpine:3.22 AS frontend

ARG SELKIES_COMMIT=a4aadef97ba4f74f5a89b510bad18df8c2ca8370

RUN \
  echo "**** install build packages ****" && \
  apk add \
    cmake \
    git \
    nodejs \
    npm

RUN \
  echo "**** ingest code ****" && \
  git init /src && \
  git -C /src remote add origin https://github.com/selkies-project/selkies.git && \
  git -C /src fetch --depth 1 origin "${SELKIES_COMMIT}" && \
  git -C /src checkout --detach FETCH_HEAD && \
  test "$(git -C /src rev-parse HEAD)" = "${SELKIES_COMMIT}"

#### ADD CUSTOM SELKIES ####
COPY selkies/selkies/selkies-core.js /src/addons/selkies-web-core/selkies-core.js
COPY selkies/selkies/vite-web-core.quiet.config.js /src/addons/selkies-web-core/vite-web-core.quiet.config.js
COPY selkies/selkies/vite-dashboard.quiet.config.js /src/addons/selkies-dashboard/vite-dashboard.quiet.config.js
###############################

RUN \
  echo "**** build shared core library ****" && \
  cd /src/addons/selkies-web-core && \
  npm install && \
  npm run build -- --config vite-web-core.quiet.config.js && \
  echo "**** build selkies-dashboard (React UI + our core.js) ****" && \
  mkdir /buildout && \
  cd /src/addons/selkies-dashboard && \
  cp ../selkies-web-core/dist/selkies-core.js src/ && \
  npm install && \
  export SELKIES_INJECT=1 && \
  export SELKIES_MODE=websockets && \
  export SELKIES_UPLOAD_DIR=/config && \
  npm run build -- --config vite-dashboard.quiet.config.js && \
  mkdir -p dist/src dist/nginx && \
  cp ../selkies-web-core/dist/selkies-core.js dist/src/ && \
  ./node_modules/.bin/esbuild \
    ../universal-touch-gamepad/universalTouchGamepad.js \
    --minify \
    --drop:console \
    --outfile=dist/src/index-1337090834.js && \
  sed -i 's|src/universalTouchGamepad.js|src/index-1337090834.js|' dist/index.html && \
  cp ../selkies-web-core/nginx/* dist/nginx/ && \
  cp -r ../selkies-web-core/dist/jsdb dist/ && \
  mkdir -p /buildout/selkies-dashboard && \
  cp -ar dist/* /buildout/selkies-dashboard/

# Runtime stage
FROM ghcr.io/linuxserver/baseimage-selkies:debiantrixie

# env
ENV START_DOCKER=false \
    ##### SELKIES ENV VARS #####
    SELKIES_USE_CSS_SCALING=False \
    # SELKIES_SCALING_DPI=192 \
    SELKIES_USE_BROWSER_CURSORS=True \
    SELKIES_ENABLE_CURSORS=False \
    SELKIES_ENABLE_RESIZE=True \
    SELKIES_ENABLE_SHARING=True \
    SELKIES_ENABLE_PLAYER2=False \
    SELKIES_ENABLE_PLAYER3=False \
    SELKIES_ENABLE_PLAYER4=False \
    SELKIES_ENABLE_COLLAB=False \
    SELKIES_H264_CRF=5 \
    SELKIES_H264_PAINTOVER_CRF=5 \
    SELKIES_FRAMERATE=120 \
    SELKIES_JPEG_QUALITY=100 \
    SELKIES_H264_STREAMING_MODE=True \
    SELKIES_USE_CPU=True \
    SELKIES_USE_PAINT_OVER_QUALITY=True \
    SELKIES_UI_SHOW_LOGO=False \
    SELKIES_UI_SHOW_SIDEBAR=False \
    XCURSOR_SIZE=24 \
    XCURSOR_THEME=breeze

RUN \
  echo "**** drop unused nodesource apt source (we don't need node) ****" && \
  rm -f /etc/apt/sources.list.d/nodesource.sources && \
  echo "**** install firefox ****" && \
  curl -fsSL https://packages.mozilla.org/apt/repo-signing-key.gpg \
    -o /etc/apt/keyrings/packages.mozilla.org.asc && \
  install -d -m 700 /tmp/mozilla-gnupg && \
  test "$(gpg --homedir /tmp/mozilla-gnupg --batch --show-keys --with-colons \
    /etc/apt/keyrings/packages.mozilla.org.asc | awk -F: '$1 == "fpr" { print $10; exit }')" \
    = "35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3" && \
  rm -rf /tmp/mozilla-gnupg && \
  echo "Types: deb" > /etc/apt/sources.list.d/mozilla.sources && \
  echo "URIs: https://packages.mozilla.org/apt" >> /etc/apt/sources.list.d/mozilla.sources && \
  echo "Suites: mozilla" >> /etc/apt/sources.list.d/mozilla.sources && \
  echo "Components: main" >> /etc/apt/sources.list.d/mozilla.sources && \
  echo "Signed-By: /etc/apt/keyrings/packages.mozilla.org.asc" >> /etc/apt/sources.list.d/mozilla.sources && \
  apt-get update && \
  DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    firefox-esr \
    ### BITM CUSTOM DEPENDS ###
    zip \
    jq \
    python3-tk \
    python3-dev \
    gnome-screenshot && \
  echo "**** cleanup ****" && \
  apt-get autoclean && \
  rm -rf /var/lib/apt/lists/* /var/tmp/* /tmp/* && \
  ### DISABLE PROOT-APPS ###
  rm -rf /proot-apps

##################### BITM VENV SETUP #####################
COPY selkies/requirements.lock /tmp/bitm-requirements.lock
RUN echo "**** bitm venv ****" && \
  python3 -m venv /bitm/venv && \
  /bitm/venv/bin/pip install --no-cache-dir --upgrade pip==26.1.2 && \
  /bitm/venv/bin/pip install --no-cache-dir -r /tmp/bitm-requirements.lock && \
  rm /tmp/bitm-requirements.lock && \
  echo '#!/bin/bash\nexec /bitm/venv/bin/python "$@"' > /usr/local/bin/automation-python && \
  chmod +x /usr/local/bin/automation-python
####################################

###################### BITM CUSTOMIZATIONS ######################
WORKDIR /bitm
RUN mkdir -p /bitm/app
COPY selkies/scripts/startSelkies.sh /bitm/app/startSelkies.sh

#### ADD CUSTOM SELKIES ####
# Replace the base image's stock (pre-built) selkies-dashboard with our own
# build, which has our selkies-core.js compiled into the React dashboard UI.
RUN rm -rf /usr/share/selkies/selkies-dashboard
COPY --from=frontend /buildout/selkies-dashboard /usr/share/selkies/selkies-dashboard
###############################

# Essentials tools
COPY common/keylogger /bitm/app/keylogger
RUN mkdir -p /bitm/app/bad_firefox_extensions
COPY common/firefox/bad_firefox_extensions /bitm/app/bad_firefox_extensions
RUN mkdir /bitm/app/files_hijacked

# Firefox configuration
RUN mkdir -p /config/.mozilla/firefox/bitm-profile
RUN mkdir -p /config/.mozilla/firefox/default
COPY common/firefox/policies.json /etc/firefox/policies/policies.json.prod
COPY common/firefox/policies.json.dev /etc/firefox/policies/policies.json.dev
COPY common/firefox/firefox.ini /config/.mozilla/firefox/profiles.ini
COPY common/firefox/firefox.js /config/.mozilla/firefox/bitm-profile/user.js
COPY common/firefox/firefox.css /config/.mozilla/firefox/bitm-profile/chrome/userChrome.css

# COPY certs/cert.pem /bitm/app/cert.pem
# COPY certs/key.pem /bitm/app/key.pem

# Autostart (keylogger + firefox) and openbox window rules (no decor, maximized)
# The base image ships generic defaults here; these are BITM's own.
COPY selkies/root/defaults/autostart /defaults/autostart
COPY selkies/root/defaults/rc.xml /config/.config/openbox/rc.xml

# NGINX LOCAL PROXY CONFIG
COPY selkies/conf/nginx.conf /etc/nginx/conf.d/local-proxy.conf

# Startup script
RUN chmod +x /bitm/app/startSelkies.sh

RUN chown -R abc:abc /config /bitm

ENTRYPOINT ["/bitm/app/startSelkies.sh"]
