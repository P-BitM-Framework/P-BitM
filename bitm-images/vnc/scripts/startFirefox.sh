#!/bin/bash

firefox_args=(
    --new-window
    "${URL:-about:blank}"
    --profile /bitm/.mozilla/firefox/bitm-profile
)

if [ "${MODE:-}" = "kiosk" ]; then
    firefox_args+=(--kiosk)
fi

firefox_args+=(--width 1920 --height 1080)

exec /usr/bin/firefox "${firefox_args[@]}"
