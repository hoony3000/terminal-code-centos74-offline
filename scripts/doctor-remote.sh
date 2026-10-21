#!/bin/bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")" && pwd -P)
id
cat /etc/centos-release 2>/dev/null || true
uname -rm
getconf GNU_LIBC_VERSION
"$ROOT/code-server/lib/node" --version
"$ROOT/bin/tode" --version
"$ROOT/bin/code-server" --version
"$ROOT/code-server/lib/node" -e 'const pty=require(process.argv[1]);const t=pty.spawn("/bin/bash",["--noprofile","--norc","-c","printf PTY_OK"],{env:process.env});let s="";t.onData(x=>s+=x);t.onExit(()=>{console.log(s);process.exit(s.includes("PTY_OK")?0:1)})' "$ROOT/code-server/lib/vscode/node_modules/node-pty"
"$ROOT/bin/tode" --serve --prepare
echo DOCTOR_OK
