#!/bin/sh
set -eu
SELF=$(readlink -f -- "$0")
ROOT=$(CDPATH= cd -- "$(dirname -- "$SELF")/.." && pwd -P)
export TODE_INSTALL_ROOT="$ROOT/app"
export XDG_DATA_HOME="$ROOT/var/data"
export XDG_STATE_HOME="$ROOT/var/state"
export XDG_CACHE_HOME="$ROOT/var/cache"
export XDG_CONFIG_HOME="$ROOT/var/config"
export ELECTRON_RUN_AS_NODE=1
exec "$ROOT/app/node_modules/@zenbu-labs/pixel/electron/dist/pixel" "$ROOT/app/dist/main.js" "$@"
