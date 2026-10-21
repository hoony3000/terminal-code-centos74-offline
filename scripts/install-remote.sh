#!/bin/bash
set -euo pipefail
SOURCE=$(cd -- "$(dirname -- "$0")" && pwd -P)
TARGET=${1:-"$HOME/.local/lib/tode-centos74"}
LINK_USER_BIN=0
if [ "$#" -eq 0 ]; then
  LINK_USER_BIN=1
  [ ! -e "$HOME/.local/bin/tode" ] && [ ! -L "$HOME/.local/bin/tode" ] || { echo 'A tode command already exists; specify a separate absolute install path.' >&2; exit 2; }
fi
case "$TARGET" in /*) ;; *) echo 'Use an absolute install path.' >&2; exit 2;; esac
case "$TARGET" in *:*|*$'\n'*|*' '*) echo 'Install path must not contain spaces, colons or newlines.' >&2; exit 2;; esac
[ "$(uname -m)" = x86_64 ] || { echo 'x86_64 is required.' >&2; exit 2; }
if [ "$SOURCE" != "$TARGET" ]; then
  [ ! -e "$TARGET" ] || { echo "Already exists: $TARGET" >&2; exit 2; }
  mkdir -p -- "$(dirname -- "$TARGET")"
  cp -a -- "$SOURCE" "$TARGET"
fi
LIB="$TARGET/runtime/lib"
PATCH="$TARGET/tools/patchelf"
while IFS= read -r -d '' file; do
  [ "$(head -c 4 "$file")" = $'\177ELF' ] || continue
  interpreter=$("$PATCH" --print-interpreter "$file" 2>/dev/null || true)
  if [ -n "$interpreter" ]; then
    previous=$("$PATCH" --print-rpath "$file" 2>/dev/null || true)
    "$PATCH" --force-rpath --set-interpreter "$LIB/ld-linux-x86-64.so.2" --set-rpath "$LIB${previous:+:$previous}" "$file"
  fi
done < <(find "$TARGET/code-server" "$TARGET/app/node_modules" -type f \( -perm /111 -o -name '*.node' -o -name '*.so' -o -name '*.so.*' \) -print0)
mkdir -p "$TARGET/var/data" "$TARGET/var/state" "$TARGET/var/cache"
"$TARGET/code-server/lib/node" --version
"$TARGET/bin/tode" --version
if [ "$LINK_USER_BIN" -eq 1 ]; then
  mkdir -p "$HOME/.local/bin"
  ln -s "$TARGET/bin/tode" "$HOME/.local/bin/tode"
fi
printf '%s\n' "Installed: $TARGET" "Start: $TARGET/bin/tode --serve /absolute/project/path"
