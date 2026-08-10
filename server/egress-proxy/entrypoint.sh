#!/bin/sh
set -eu

exec squid -N -f /etc/squid/squid.conf
