#!/usr/bin/env python3
"""Build the CentOS 7.4 x86_64 Claude Code bundle with Python 3.10+."""

import argparse
import gzip
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile

from build_bundle import ROOT, deb_data, download, sha256


SCRIPTS = ROOT / "scripts" / "claude-code"
MUSL_FILES = {
    "usr/lib/x86_64-linux-musl/libc.so": "lib/ld-musl-x86_64.so.1",
    "usr/share/doc/musl/copyright": "licenses/musl.copyright",
}
EXECUTABLES = {"claude", "claude-bin", "lib/ld-musl-x86_64.so.1"}
TAR_MTIME = 946684800  # January 1, 2000. CentOS 7 tar warns about the Unix epoch.


def extract_musl(package, folder):
    with tarfile.open(fileobj=deb_data(package), mode="r:*") as archive:
        for member in archive:
            destination = MUSL_FILES.get(str(PurePosixPath(member.name)))
            if destination is not None:
                if not member.isfile():
                    raise ValueError(f"Expected a regular file in musl package: {member.name}")
                with archive.extractfile(member) as source, (folder / destination).open("wb") as target:
                    shutil.copyfileobj(source, target)
    for destination in MUSL_FILES.values():
        if not (folder / destination).is_file():
            raise ValueError(f"Missing musl package member for {destination}")


def build(lock, cache, output):
    version = lock["claude_version"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("Expected a pinned Claude Code version")
    binary = download(lock["claude"], cache)
    musl = download(lock["musl"], cache)

    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output, prefix=".building-claude-") as temp:
        work = Path(temp)
        folder = work / f"claude-code-{version}-centos74-x64"
        (folder / "lib").mkdir(parents=True)
        (folder / "licenses").mkdir()
        extract_musl(musl, folder)
        shutil.copyfile(binary, folder / "claude-bin")
        for filename in ("claude", "install.sh", "doctor.sh"):
            shutil.copyfile(SCRIPTS / filename, folder / filename)
        (folder / "version.txt").write_text(version + "\n", encoding="ascii", newline="\n")
        (folder / "manifest.json").write_text(
            json.dumps(lock, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        payload = sorted(path for path in folder.rglob("*") if path.is_file())
        (folder / "SHA256SUMS").write_text(
            "".join(f"{sha256(path)}  {path.relative_to(folder).as_posix()}\n" for path in payload),
            encoding="ascii", newline="\n",
        )

        name = f"{folder.name}.tar.gz"
        pending = work / name
        with (
            pending.open("wb") as target,
            gzip.GzipFile(filename="", fileobj=target, mode="wb", mtime=0, compresslevel=1) as compressed,
            tarfile.open(fileobj=compressed, mode="w") as archive,
        ):
            for path in sorted([folder, *folder.rglob("*")]):
                relative = path.relative_to(folder).as_posix()
                info = archive.gettarinfo(str(path), arcname=path.relative_to(work).as_posix())
                info.uid = info.gid = 0
                info.mtime = TAR_MTIME
                info.uname = info.gname = ""
                info.mode = 0o755 if path.is_dir() or relative in EXECUTABLES else 0o644
                if info.isfile():
                    with path.open("rb") as source:
                        archive.addfile(info, source)
                else:
                    archive.addfile(info)

        checksum = work / f"{name}.sha256"
        checksum.write_text(f"{sha256(pending)}  {name}\n", encoding="ascii", newline="\n")
        pending.replace(output / name)
        checksum.replace(output / checksum.name)
        print(output / name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=ROOT / "claude-bundle-lock.json")
    parser.add_argument("--cache", type=Path, default=ROOT / ".bundle-cache")
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    try:
        build(json.loads(args.lock.read_text(encoding="utf-8")), args.cache, args.out)
    except (OSError, ValueError, RuntimeError, KeyError, tarfile.TarError) as error:
        parser.exit(1, f"Bundle failed: {error}\n")


if __name__ == "__main__":
    main()
