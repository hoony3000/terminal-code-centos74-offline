#!/bin/bash
set -euo pipefail

bundle=$(cd -- "$(dirname -- "$0")" && pwd -P)
target=${1:-"$bundle"}
printf 'Kernel: %s\n' "$(uname -r)"
printf 'System libc: %s\n' "$(getconf GNU_LIBC_VERSION)"
printf 'Architecture: %s\n' "$(uname -m)"
output=$("$target/claude" --version)
printf '%s\n' "$output"
expected=$(cat -- "$bundle/version.txt")
[[ $output == "$expected (Claude Code)" ]] || {
    printf 'Expected Claude Code %s.\n' "$expected" >&2
    exit 1
}
"$target/claude" --help >/dev/null
printf 'CLAUDE_DOCTOR_OK\n'
