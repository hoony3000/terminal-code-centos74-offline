#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
command -v ghostty >/dev/null || { echo 'Ghostty is required in this WSL distribution. See README-KO.txt.' >&2; exit 2; }
exec ghostty --config-default-files=false --config-file="$ROOT/ghostty.conf" -e "$ROOT/bin/tode" "$@"
