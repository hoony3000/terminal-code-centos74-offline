#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "$0")"
bundle=$(pwd -P)
[[ $(uname -m) == x86_64 ]] || { printf 'Linux x86_64 is required.\n' >&2; exit 1; }
sha256sum -c SHA256SUMS
mapfile -t version < version.txt
[[ ${version[0]:-} =~ ^[0-9]+\.[0-9]+\.[0-9]+$ && ${version[1]:-} =~ ^[0-9a-f]{40}$ ]] ||
  { printf 'Invalid version or commit.\n' >&2; exit 1; }

installation="$bundle/vscode-${version[0]}"
if [[ ! -e "$installation" ]]; then
  stage=$(mktemp -d "$bundle/.offline-client.XXXXXXXX")
  trap 'rm -rf -- "$stage"' EXIT
  tar -xzf "VSCode-linux-x64-${version[0]}.tar.gz" --strip-components=1 -C "$stage"
  [[ -x "$stage/bin/code" ]]
  mv -T -n -- "$stage" "$installation"
fi

settings="$installation/data/user-data/User"
mkdir -p -- "$settings"
if [[ ! -e "$settings/settings.json" ]]; then
  cp -- settings.json "$settings/"
fi

cli="$installation/bin/code"
actual=$("$cli" --version)
grep -Fxq -- "${version[1]}" <<< "$actual"
while IFS= read -r extension; do
  [[ $extension =~ ^[A-Za-z0-9.+_~-]+\.vsix$ ]]
  "$cli" --install-extension "$bundle/$extension"
done < extensions.txt

printf 'Start: %s\n' "$installation/code"
