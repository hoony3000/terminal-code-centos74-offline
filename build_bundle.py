#!/usr/bin/env python3
"""Build CentOS 7.4 offline bundles for VS Code Remote-SSH or Claude Code."""

import argparse
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import tempfile
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
import zipfile


ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts" / "remote-ssh"
CLIENT_SCRIPTS = {"windows-x64": "install.ps1", "linux-x64": "install-client.sh"}
REQUIRED_LIBRARIES = {
    "ld-linux-x86-64.so.2", "libc.so.6", "libdl.so.2", "libgcc_s.so.1",
    "libm.so.6", "libpthread.so.0", "libstdc++.so.6",
}

CLAUDE_SCRIPTS = ROOT / "scripts" / "claude-code"
MUSL_FILES = {
    "usr/lib/x86_64-linux-musl/libc.so": "lib/ld-musl-x86_64.so.1",
    "usr/share/doc/musl/copyright": "licenses/musl.copyright",
}
CLAUDE_EXECUTABLES = {"claude", "claude-bin", "lib/ld-musl-x86_64.so.1"}
TAR_MTIME = 946684800  # January 1, 2000. CentOS 7 tar warns about the Unix epoch.


def sha256(path):
    with path.open("rb") as reader:
        digest = hashlib.sha256()
        for chunk in iter(lambda: reader.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(asset, cache):
    filename, expected, url = (asset[key] for key in ("filename", "sha256", "url"))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+_~-]*", filename):
        raise ValueError(f"Invalid asset filename: {filename!r}")
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or not url.startswith("https://"):
        raise ValueError(f"Expected a pinned HTTPS URL and SHA-256 for {filename}")
    folder = cache / expected
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    if path.is_file() and sha256(path) == expected:
        print(f"Verified cache: {filename}", flush=True)
        return path

    request = Request(url, headers={"User-Agent": "vscode-remote-ssh-offline-bundle/1"})
    print(f"Downloading: {filename}", flush=True)
    for attempt in range(3):
        with tempfile.NamedTemporaryFile(dir=folder, delete=False) as handle:
            pending = Path(handle.name)
        try:
            with urlopen(request, timeout=120) as source, pending.open("wb") as target:
                if not source.geturl().startswith("https://"):
                    raise ValueError(f"Unexpected non-HTTPS redirect for {filename}")
                shutil.copyfileobj(source, target, length=1024 * 1024)
            if sha256(pending) != expected:
                raise ValueError(f"SHA-256 mismatch for {filename}: {url}")
            pending.replace(path)
            return path
        except (OSError, URLError) as error:
            if attempt == 2:
                raise RuntimeError(f"Download failed for {filename}: {url}: {error}") from error
            time.sleep(2 ** attempt)
        finally:
            pending.unlink(missing_ok=True)


def deb_data(path):
    with path.open("rb") as package:
        if package.read(8) != b"!<arch>\n":
            raise ValueError(f"Invalid Debian archive: {path.name}")
        while header := package.read(60):
            if len(header) != 60 or header[58:] != b"`\n":
                raise ValueError(f"Invalid member header: {path.name}")
            name = header[:16].decode("ascii").strip().rstrip("/")
            size = int(header[48:58])
            if name.startswith("data.tar"):
                data = package.read(size)
                if len(data) != size:
                    raise ValueError(f"Truncated Debian archive: {path.name}")
                return io.BytesIO(data)
            package.seek(size + size % 2, io.SEEK_CUR)
    raise ValueError(f"No data.tar member: {path.name}")


def add_tar_member(output, archive, member, name):
    item = copy.copy(member)
    item.name = name
    item.uid = item.gid = 0
    item.uname = item.gname = ""
    item.pax_headers = {}
    item.mode &= 0o777
    if item.isfile():
        with archive.extractfile(member) as source:
            output.addfile(item, source)
    else:
        output.addfile(item)


def runtime_archive(path, assets, patchelf, license_file, notices):
    library_paths = {"lib/x86_64-linux-gnu", "usr/lib/x86_64-linux-gnu"}
    libraries = {}
    notices.mkdir()
    with (
        path.open("wb") as destination,
        gzip.GzipFile(filename="", fileobj=destination, mode="wb", mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w") as output,
    ):
        for asset, package in assets:
            package_name = asset["package"]
            copyright_path = f"usr/share/doc/{package_name}/copyright"
            with tarfile.open(fileobj=deb_data(package), mode="r:*") as archive:
                for member in archive:
                    member_path = PurePosixPath(member.name)
                    name = member_path.name
                    if str(member_path) == copyright_path and member.isfile():
                        with archive.extractfile(member) as source:
                            (notices / f"{package_name}.copyright").write_bytes(source.read())
                    if str(member_path.parent) not in library_paths or not (
                        member.isfile() or member.issym()
                    ):
                        continue
                    if name in libraries:
                        raise ValueError(f"Duplicate runtime library: {name}")
                    if member.issym() and not re.fullmatch(r"[A-Za-z0-9_.+-]+", member.linkname):
                        raise ValueError(f"Unexpected runtime symlink: {name} -> {member.linkname}")
                    libraries[name] = member.linkname if member.issym() else None
                    add_tar_member(output, archive, member, f"lib/{name}")

        missing = REQUIRED_LIBRARIES - libraries.keys()
        unresolved = {target for target in libraries.values() if target and target not in libraries}
        if missing or unresolved:
            raise ValueError(f"Missing runtime files: {', '.join(sorted(missing | unresolved))}")

        with tarfile.open(patchelf, "r:gz") as archive:
            tool = next(
                (member for member in archive if PurePosixPath(member.name) == PurePosixPath("bin/patchelf")),
                None,
            )
            if tool is None or not tool.isfile() or not tool.mode & 0o111:
                raise ValueError("patchelf archive must contain an executable bin/patchelf")
            add_tar_member(output, archive, tool, "bin/patchelf")

    for name in ("libc6.copyright", "gcc-10-base.copyright"):
        if not (notices / name).is_file():
            raise ValueError(f"Missing third-party notice: {name}")
    shutil.copyfile(license_file, notices / "patchelf-COPYING")


def verify_server(server, lock):
    with tarfile.open(server, "r:gz") as archive:
        files = {}
        for member in archive:
            path = PurePosixPath(member.name)
            if len(path.parts) > 1:
                files["/".join(path.parts[1:])] = member
        for name in ("node", "bin/code-server", "product.json", "package.json"):
            if name not in files or not files[name].isfile():
                raise ValueError(f"Official server archive is missing {name}")
        node = files["node"]
        if not node.mode & 0o111:
            raise ValueError("The bundled Node binary has no execute permission")
        with archive.extractfile(node) as source:
            header = source.read(20)
        if header[:6] != b"\x7fELF\x02\x01" or header[18:20] != b"\x3e\x00":
            raise ValueError("The bundled Node is not a Linux x86_64 executable")
        with archive.extractfile(files["product.json"]) as source:
            product = json.load(source)
        with archive.extractfile(files["package.json"]) as source:
            package = json.load(source)
    if (
        product.get("commit") != lock["commit"]
        or product.get("quality") != lock["channel"]
        or package.get("version") != lock["vscode_version"]
        or package.get("nativeBuild", {}).get("target") != lock["node_version"]
    ):
        raise ValueError("Official server version, channel, commit, or Node version does not match the lock")


def verify_extensions(extensions, vscode_version):
    installed = set()
    for asset, vsix in extensions:
        with zipfile.ZipFile(vsix) as archive:
            package = json.loads(archive.read("extension/package.json"))
        identifier = f"{package['publisher']}.{package['name']}".lower()
        engine = package["engines"]["vscode"]
        if (
            identifier != asset["id"]
            or package["version"] != asset["version"]
            or engine != asset["engines_vscode"]
        ):
            raise ValueError(f"VSIX metadata does not match the lock: {vsix.name}")
        if not re.fullmatch(r"\^\d+\.\d+\.\d+", engine):
            raise ValueError(f"Unsupported VS Code engine range in {vsix.name}: {engine}")
        minimum = tuple(int(part) for part in engine[1:].split("."))
        actual = tuple(int(part) for part in vscode_version.split("."))
        if actual[0] != minimum[0] or actual < minimum:
            raise ValueError(f"{vsix.name} requires VS Code {engine}")
        dependencies = package.get("extensionPack", []) + package.get("extensionDependencies", [])
        missing = {item.lower() for item in dependencies} - installed
        if missing:
            raise ValueError(f"{vsix.name} needs preceding VSIX files: {', '.join(sorted(missing))}")
        installed.add(identifier)


def write_metadata(folder, lock, platform, assets):
    manifest = {
        key: lock[key] for key in ("vscode_version", "channel", "commit", "node_version", "runtime_sources")
    }
    manifest.update({"target": platform, "sources": assets})
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (folder / "version.txt").write_text(
        "\n".join([lock["vscode_version"], lock["commit"], lock["node_version"]]) + "\n",
        encoding="ascii",
        newline="\n",
    )
    contents = sorted(path for path in folder.rglob("*") if path.is_file())
    lines = [f"{sha256(path)}  {path.relative_to(folder).as_posix()}\n" for path in contents]
    (folder / "SHA256SUMS").write_text("".join(lines), encoding="ascii", newline="\n")


def copy_asset(asset, folder):
    info, path = asset
    shutil.copyfile(path, folder / info["filename"])


def build(lock, platform, cache, output):
    build_id = lock["vscode_version"]
    if not (
        re.fullmatch(r"\d+\.\d+\.\d+", build_id)
        and re.fullmatch(r"[0-9a-f]{40}", lock["commit"])
        and re.fullmatch(r"\d+\.\d+\.\d+", lock["node_version"])
        and lock["channel"] == "stable"
    ):
        raise ValueError("The lock must contain a Stable desktop version, server commit, and Node version")

    client_assets = [lock["desktops"][platform], *lock["extensions"]]
    runtime = lock["runtime_packages"]
    server_assets = [lock["server"], *runtime, lock["patchelf"], lock["patchelf_license"]]
    files = {asset["filename"]: download(asset, cache) for asset in client_assets + server_assets}
    server = files[lock["server"]["filename"]]
    extensions = [(asset, files[asset["filename"]]) for asset in lock["extensions"]]
    verify_server(server, lock)
    verify_extensions(extensions, build_id)

    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output, prefix=".building-") as temp:
        work = Path(temp)
        client_folder = work / f"vscode-{build_id}-client-{platform}"
        client_folder.mkdir()
        for asset in client_assets:
            copy_asset((asset, files[asset["filename"]]), client_folder)
        script = CLIENT_SCRIPTS[platform]
        shutil.copyfile(SCRIPTS / script, client_folder / script)
        shutil.copyfile(SCRIPTS / "settings.json", client_folder / "settings.json")
        (client_folder / "extensions.txt").write_text(
            "".join(f"{asset['filename']}\n" for asset, _ in extensions),
            encoding="ascii",
            newline="\n",
        )
        write_metadata(client_folder, lock, platform, client_assets)
        client_archive = work / f"{client_folder.name}.zip"
        with zipfile.ZipFile(client_archive, "w", compression=zipfile.ZIP_STORED) as archive:
            for path in sorted(client_folder.iterdir()):
                archive.write(path, f"{client_folder.name}/{path.name}")

        server_folder = work / f"vscode-{build_id}-server-centos74-x64"
        server_folder.mkdir()
        shutil.copyfile(server, server_folder / "vscode-server-linux-x64.tar.gz")
        runtime_archive(
            server_folder / "runtime.tar.gz",
            [(asset, files[asset["filename"]]) for asset in runtime],
            files[lock["patchelf"]["filename"]],
            files[lock["patchelf_license"]["filename"]],
            server_folder / "licenses",
        )
        for script in ("install.sh", "doctor.sh"):
            shutil.copyfile(SCRIPTS / script, server_folder / script)
        write_metadata(server_folder, lock, "centos74-x64", server_assets)
        server_archive = work / f"{server_folder.name}.tar.gz"
        with tarfile.open(server_archive, "w:gz", compresslevel=1) as archive:
            archive.add(server_folder, arcname=server_folder.name)

        for path in (client_archive, server_archive):
            digest = sha256(path)
            destination = output / path.name
            path.replace(destination)
            checksum = output / f"{path.name}.sha256"
            pending_checksum = work / checksum.name
            pending_checksum.write_text(f"{digest}  {path.name}\n", encoding="ascii", newline="\n")
            pending_checksum.replace(checksum)
            print(destination)


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


def build_claude(lock, cache, output):
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
            shutil.copyfile(CLAUDE_SCRIPTS / filename, folder / filename)
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
                info.mode = 0o755 if path.is_dir() or relative in CLAUDE_EXECUTABLES else 0o644
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
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--client", choices=CLIENT_SCRIPTS, help="VS Code client platform (default: windows-x64)")
    target.add_argument("--claude", action="store_true", help="build the Claude Code server bundle")
    parser.add_argument("--lock", type=Path, help="use a custom lock file for the selected bundle")
    parser.add_argument("--cache", type=Path, default=ROOT / ".bundle-cache")
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    try:
        default_lock = "claude-bundle-lock.json" if args.claude else "bundle-lock.json"
        lock = json.loads((args.lock or ROOT / default_lock).read_text(encoding="utf-8"))
        if args.claude:
            build_claude(lock, args.cache, args.out)
        else:
            build(lock, args.client or "windows-x64", args.cache, args.out)
    except (OSError, ValueError, RuntimeError, KeyError, tarfile.TarError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Bundle failed: {error}\n")


if __name__ == "__main__":
    main()
