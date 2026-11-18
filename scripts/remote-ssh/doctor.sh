#!/usr/bin/env bash
set -euo pipefail

bundle=$(cd -- "$(dirname -- "$0")" && pwd -P)
mapfile -t version < "$bundle/version.txt"
commit=${version[1]:-}
[[ $commit =~ ^[0-9a-f]{40}$ ]] || { printf 'Invalid server commit.\n' >&2; exit 1; }
target=${1:-"$HOME/.vscode-server/bin/$commit"}
cd -- "$target"

# Test the application's own loader and libraries, independently of the caller's environment.
unset LD_LIBRARY_PATH LD_PRELOAD VSCODE_SERVER_CUSTOM_GLIBC_LINKER
unset VSCODE_SERVER_CUSTOM_GLIBC_PATH VSCODE_SERVER_PATCHELF_PATH
printf 'Kernel: %s\n' "$(uname -r)"
printf 'System libc: %s\n' "$(getconf GNU_LIBC_VERSION)"
node_version=$(./node --version)
[[ $node_version == "v${version[2]}" ]] ||
  { printf 'Expected Node v%s, got %s\n' "${version[2]}" "$node_version" >&2; exit 1; }
printf 'Bundled Node: %s\n' "$node_version"
server_version=$(./bin/code-server --version)
printf '%s\n' "$server_version"
grep -Fxq -- "${version[0]}" <<< "$server_version"
grep -Fxq -- "$commit" <<< "$server_version"

rg=./node_modules/@vscode/ripgrep-universal/bin/linux-x64/rg
[[ -x "$rg" ]] || { printf 'Missing VS Code ripgrep executable.\n' >&2; exit 1; }
"$rg" --version >/dev/null

./node --input-type=commonjs - <<'JS'
const pty = require("node-pty");
const child = pty.spawn("/bin/bash", ["--noprofile", "--norc", "-c", "printf VS_CODE_PTY_OK"], {
    name: "xterm",
    cols: 80,
    rows: 24,
    cwd: process.cwd(),
    env: process.env,
});
let output = "";
const timer = setTimeout(() => {
    console.error("The VS Code terminal did not finish within five seconds.");
    child.kill();
    process.exit(1);
}, 5000);
child.onData(data => { output += data; });
child.onExit(({ exitCode }) => {
    clearTimeout(timer);
    if (exitCode !== 0 || !output.includes("VS_CODE_PTY_OK")) {
        console.error("VS Code terminal test failed", exitCode, JSON.stringify(output));
        process.exitCode = 1;
    }
});
JS
printf 'SERVER_DOCTOR_OK\n'
