#!/bin/bash
set -euo pipefail

bundle=$(cd -- "$(dirname -- "$0")" && pwd -P)
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || {
    printf 'This bundle requires Linux x86_64.\n' >&2
    exit 1
}
(cd -- "$bundle" && sha256sum --check --quiet SHA256SUMS)
version=$(cat -- "$bundle/version.txt")
[[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
    printf 'Invalid Claude Code version.\n' >&2
    exit 1
}

versions="$HOME/.local/share/claude-code-centos74/versions"
target="$versions/$version"
bin="$HOME/.local/bin"
launcher="$bin/claude"
mkdir -p -- "$versions" "$bin"

exec 9>"$versions/.install.lock"
flock -x 9
activate=true
if [[ -L $launcher || -e $launcher ]]; then
    current=$(readlink -- "$launcher" || :)
    if [[ ${current%/*/*} != "$versions" || ${current##*/} != claude ]]; then
        activate=false
    fi
fi

if [[ -e $target || -L $target ]]; then
    [[ -d $target && ! -L $target ]] &&
        (cd -- "$target" && sha256sum --check --quiet "$bundle/SHA256SUMS") || {
        printf 'Existing installation failed checksum verification at %s\n' "$target" >&2
        exit 1
    }
    bash "$bundle/doctor.sh" "$target"
else
    staging=$(mktemp -d "$versions/.install.XXXXXXXX")
    trap 'rm -rf -- "$staging"' EXIT
    cp -R -- "$bundle/." "$staging/"
    bash "$bundle/doctor.sh" "$staging"
    mv -T -- "$staging" "$target"
fi

if "$activate"; then
    if [[ -n ${current:-} ]]; then
        link_stage=$(mktemp -d "$bin/.claude.XXXXXXXX")
        trap 'rm -rf -- "$link_stage"' EXIT
        ln -s -- "$target/claude" "$link_stage/claude"
        mv -Tf -- "$link_stage/claude" "$launcher"
    else
        ln -sT -- "$target/claude" "$launcher"
    fi
    printf 'Launcher: %s\n' "$launcher"
else
    printf 'Existing launcher kept at %s\n' "$launcher"
fi
printf 'Installed executable: %s\n' "$target/claude"
