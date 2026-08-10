#!/bin/bash
set -Eeuo pipefail

case "${STREAM_PATH:-}" in
    ""|*[!A-Za-z0-9_-]*)
        echo "Invalid STREAM_PATH" >&2
        exit 1
        ;;
esac
case "${STREAM_COOKIE_NAME:-}" in
    ""|*[!a-z0-9_]*)
        echo "Invalid STREAM_COOKIE_NAME" >&2
        exit 1
        ;;
esac
case "${CAMPAIGN_ID:-}" in
    ""|*[!A-Za-z0-9_-]*)
        echo "Invalid CAMPAIGN_ID" >&2
        exit 1
        ;;
esac
case "${GATEWAY_AUTH_KEY:-}" in
    ""|*[!A-Za-z0-9]*)
        echo "Invalid GATEWAY_AUTH_KEY" >&2
        exit 1
        ;;
esac

sed -i "s|CAMPAIGN_ID|${CAMPAIGN_ID}|g" /etc/nginx/nginx.conf
sed -i "s|GATEWAY_AUTH_KEY|${GATEWAY_AUTH_KEY}|g" /etc/nginx/nginx.conf
sed -i "s|STREAM_PATH|${STREAM_PATH}|g" /etc/nginx/nginx.conf
sed -i "s|STREAM_COOKIE_NAME|${STREAM_COOKIE_NAME}|g" /etc/nginx/nginx.conf
mkdir -p "/storage/${CAMPAIGN_ID}"

# Keep both processes coupled: a live nginx without the application behind it
# would make the campaign look healthy while every request is failing.
python main.py &
app_pid=$!

nginx -g 'daemon off;' &
nginx_pid=$!

shutdown() {
    kill -TERM "$app_pid" "$nginx_pid" 2>/dev/null || true
    wait "$app_pid" "$nginx_pid" 2>/dev/null || true
}

trap shutdown INT TERM

# Exit as soon as either process exits, then terminate the remaining sibling.
if wait -n "$app_pid" "$nginx_pid"; then
    exit_status=0
else
    exit_status=$?
fi
shutdown
exit "$exit_status"
