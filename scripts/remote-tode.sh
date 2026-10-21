#!/bin/sh
set -eu
SELF=$(readlink -f -- "$0")
ROOT=$(CDPATH= cd -- "$(dirname -- "$SELF")/.." && pwd -P)
export TODE_INSTALL_ROOT="$ROOT/app"
export TODE_CODE_SERVER="$ROOT/bin/code-server"
export XDG_DATA_HOME="$ROOT/var/data"
export XDG_STATE_HOME="$ROOT/var/state"
export XDG_CACHE_HOME="$ROOT/var/cache"
export XDG_CONFIG_HOME="$ROOT/var/config"
exec "$ROOT/code-server/lib/node" "$ROOT/app/dist/main.js" "$@"
