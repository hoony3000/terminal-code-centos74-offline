#!/usr/bin/env bash
set -euo pipefail
umask 077

bundle=$(cd -- "$(dirname -- "$0")" && pwd -P)
die() { printf 'Install failed: %s\n' "$*" >&2; exit 1; }

[[ $(uname -m) == x86_64 ]] || die "Linux x86_64 is required."
(cd -- "$bundle" && sha256sum -c SHA256SUMS)
mapfile -t version < "$bundle/version.txt"
commit=${version[1]:-}
[[ $commit =~ ^[0-9a-f]{40}$ && ${version[2]:-} =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] ||
  die "Invalid commit or Node version in version.txt."

parent="$HOME/.vscode-server/bin"
mkdir -p -- "$parent"
parent=$(cd -- "$parent" && pwd -P)
case "$parent" in
  *:*|*$'\n'*) die "The server path cannot contain colons or newlines." ;;
esac

target="$parent/$commit"
if [[ -e "$target" || -L "$target" ]]; then
  [[ -f "$target/.offline-bundle" && ! -L "$target" ]] ||
    die "An installation already exists at $target."
  cmp -s "$bundle/SHA256SUMS" "$target/.offline-bundle" ||
    die "A different offline bundle already occupies $target."
  bash "$bundle/doctor.sh" "$target"
  exit
fi

stage=$(mktemp -d "$parent/.offline-install.XXXXXXXX")
trap 'rm -rf -- "$stage"' EXIT

tar -xzf "$bundle/vscode-server-linux-x64.tar.gz" --strip-components=1 -C "$stage"
mkdir -- "$stage/.offline-runtime"
tar -xzf "$bundle/runtime.tar.gz" -C "$stage/.offline-runtime"
cp -R -- "$bundle/licenses" "$stage/.offline-runtime/licenses"

runtime="$stage/.offline-runtime"
patch="$runtime/bin/patchelf"
loader="$runtime/lib/ld-linux-x86-64.so.2"
[[ -x "$stage/node" && -x "$stage/bin/code-server" && -x "$loader" && -x "$patch" ]] ||
  die "The server archive or the private runtime is incomplete."

printf 'Kernel: %s\n' "$(uname -r)"
printf 'Checking the bundled Node with the private loader...\n'
node_version=$("$loader" --library-path "$runtime/lib" "$stage/node" --version)
[[ $node_version == "v${version[2]}" ]] || die "Expected Node v${version[2]}, got $node_version."
"$patch" --version
# Use RPATH for libraries pulled in by native extensions as well as by Node.
rpath=$("$patch" --print-rpath "$stage/node")
"$patch" --force-rpath --set-rpath '$ORIGIN/.offline-runtime/lib'"${rpath:+:$rpath}" "$stage/node"
"$patch" --set-interpreter "$target/.offline-runtime/lib/ld-linux-x86-64.so.2" "$stage/node"

cp -- "$bundle/SHA256SUMS" "$stage/.offline-bundle"
mv -T -n -- "$stage" "$target"
[[ ! -d "$stage" ]] || die "Another process installed $target. Retry after it completes."

if ! bash "$bundle/doctor.sh" "$target"; then
  mv -T -- "$target" "$stage"
  die "The server diagnostic failed. The new installation has been withdrawn."
fi

printf 'Installed: %s\n' "$target"
