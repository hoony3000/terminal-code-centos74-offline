#!/bin/bash
set -euo pipefail
SOURCE=$(cd -- "$(dirname -- "$0")" && pwd -P)
TARGET=${1:-"$HOME/.local/lib/tode-client"}
case "$TARGET" in /*) ;; *) echo 'Use an absolute install path.' >&2; exit 2;; esac
[ ! -e "$TARGET" ] || { echo "Already exists: $TARGET" >&2; exit 2; }
mkdir -p -- "$TARGET"
tar -xzf "$SOURCE/terminal-code-linux-client.tar.gz" -C "$TARGET" --strip-components=1
"$TARGET/bin/tode" --version
printf '%s\n' "Installed: $TARGET" "Run: $TARGET/bin/open-ghostty --ssh user@host /absolute/project/path"
