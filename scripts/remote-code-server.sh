#!/bin/sh
set -eu
SELF=$(readlink -f -- "$0")
ROOT=$(CDPATH= cd -- "$(dirname -- "$SELF")/.." && pwd -P)
export XDG_CONFIG_HOME="$ROOT/var/config"
exec "$ROOT/code-server/lib/node" "$ROOT/code-server/out/node/entry.js" "$@"
