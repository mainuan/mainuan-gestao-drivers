#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only audits for Python package inputs and native runtime dependencies.

Absent ISA notes do not prove baseline code. Pair this evidence with the QEMU
startup gate; unlike Welcome, this project has no CMake/codegen to inspect.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def command(argv):
    return subprocess.check_output(argv, text=True, env={**os.environ, "LC_ALL": "C"}, timeout=60)


def environment_errors(architecture, config, packages, release):
    errors = []
    if architecture != "amd64":
        errors.append("Expected an amd64 validation environment")
    if release.get("ID") != "ubuntu" or release.get("VERSION_ID") != "26.04":
        errors.append("Expected official Ubuntu 26.04 (not the developer host)")
    if 'APT::Architecture-Variants "";' not in config:
        errors.append("APT CPU variants were not explicitly disabled")
    for line in config.splitlines():
        if line.startswith("APT::Architecture-Variants") and re.search(r'"[^"\s][^"]*"', line):
            errors.append("Enabled APT CPU variant: " + line)
    architectures = re.findall(r'^APT::Architectures:: "([^"]+)";', config, re.M)
    if architectures != ["amd64"]:
        errors.append("APT indexes must be limited to baseline amd64")
    for line in packages.splitlines():
        fields = line.split("\t")
        if len(fields) != 5:
            errors.append("Malformed installed-package evidence")
        elif fields[1] not in ("not-installed", "config-files"):
            if fields[1] != "installed":
                errors.append("Incomplete package configuration: " + line)
            if fields[2] not in ("all", "amd64") or fields[3] not in ("", "amd64"):
                errors.append("Non-baseline installed package: " + line)
    return errors


def environment():
    architecture = command(["dpkg", "--print-architecture"]).strip()
    config = command(["apt-config", "dump"])
    packages = command(["dpkg-query", "-W", "-f=${binary:Package}\t${db:Status-Status}\t${Architecture}\t${Architecture-Variant}\t${Version}\n"])
    release = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        key, separator, value = line.partition("=")
        if separator:
            release[key] = value.strip('"')
    names = ["python3", "python3-pyqt6", "python3-apt", "ubuntu-drivers-common", "packagekit",
             "libc6", "libqt6core6t64", "libqt6widgets6", "libqt6dbus6", "qemu-user", "mokutil", "openssl", "kmod", "polkitd"]
    return {"architecture": architecture, "os_release": release, "apt_config": config,
            "packages": packages, "repository_policy": command(["apt-cache", "policy", *names]),
            "source_commit": command(["git", "rev-parse", "HEAD"]).strip(),
            "working_tree": command(["git", "status", "--porcelain"]),
            "base_image": os.environ.get("MAINUAN_BASE_IMAGE", "not running in the CI image"),
            "errors": environment_errors(architecture, config, packages, release)}


def declared_isa(notes):
    requirements = re.findall(r"x86 ISA needed:\s*([^\n]+)", notes)
    for requirement in requirements:
        if any(part.strip() != "x86-64-baseline" for part in requirement.split(",")):
            raise ValueError("Non-baseline declared ISA: " + requirement)
    return requirements


def native_file(path):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        if stream.read(4) != b"\x7fELF":
            raise ValueError("Expected a native system dependency: " + str(path))
    headers = command(["readelf", "--file-header", "--notes", "--wide", str(path)])
    if not re.search(r"Class:\s+ELF64", headers) or not re.search(r"Machine:\s+Advanced Micro Devices X86-64", headers):
        raise ValueError("Not an ELF64 AMD64 runtime dependency: " + str(path))
    try:
        notes = declared_isa(headers)
    except ValueError as error:
        raise ValueError(str(path) + ": " + str(error)) from error
    owner = subprocess.run(["dpkg-query", "-S", str(path)], capture_output=True, text=True, timeout=30)
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "needed": notes, "isa_note_declared": bool(notes),
            "owner": owner.stdout.strip() or "not identified by dpkg-query -S",
            "readelf": headers}


def static_resolution(package):
    result = {}
    files = command(["dpkg-query", "-L", package]).splitlines()
    for name in files:
        path = Path(name)
        if path.is_file():
            with path.open("rb") as stream:
                if stream.read(4) != b"\x7fELF":
                    continue
            output = command(["ldd", str(path)])
            if "not found" in output:
                raise ValueError("Unresolved PackageKit dependency: " + output)
            linked = re.findall(r"(?:=>\s+|^\s*)(/[^\s]+)", output, re.M)
            for dependency in [name, *linked]:
                resolved = str(Path(dependency).resolve())
                if resolved not in result:
                    result[resolved] = native_file(resolved)
    return list(result.values())


def dependencies(report_path):
    startup = json.loads(Path(report_path).read_text())
    paths = set()
    for run in startup["runs"]:
        if not run.get("success"):
            raise ValueError("Startup was not successful")
        paths.update(run["loaded_elf"])
    if not paths:
        raise ValueError("No actually loaded client ELF dependencies recorded")
    client = [native_file(path) for path in sorted(paths)]
    # Daemons/helpers are separate processes. Inspect installed ELF and ldd,
    # without executing their operations or calling these UI process maps.
    daemon = static_resolution("packagekit")
    if not daemon:
        raise ValueError("PackageKit native daemon/backend not found")
    helpers = {}
    for package in ("ubuntu-drivers-common", "mokutil", "openssl", "kmod", "polkitd"):
        status = subprocess.run(["dpkg-query", "-W", "-f=${db:Status-Status}", package], capture_output=True, text=True)
        helpers[package] = static_resolution(package) if status.returncode == 0 and status.stdout == "installed" else "not installed"
    return {"startup_baseline_emulated": startup["baseline_emulated"], "startup_cpu": startup["cpu"],
            "client_actually_loaded": client, "packagekit_static_resolution": daemon,
            "system_helpers_static_resolution": helpers,
            "limits": "ISA notes are declarations, not instruction proofs. QEMU tests client startup, not the full ISO or daemon transactions."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("environment", "dependencies"))
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-only", action="store_true", help="Record developer-host differences; never use to pass CI")
    args = parser.parse_args()
    if args.kind == "dependencies" and not args.path:
        parser.error("A startup JSON report is required")
    if args.report_only and args.kind != "environment":
        parser.error("Report-only is restricted to developer environment inventory")
    try:
        result = environment() if args.kind == "environment" else dependencies(args.path)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        if result.get("errors") and not args.report_only:
            raise ValueError("; ".join(result["errors"]))
        print("Audit written:", args.output)
        if args.report_only:
            print("INVENTORY ONLY, NOT A BASELINE PASS:", result["errors"])
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, "CPU/runtime audit failed: %s\n" % error)


if __name__ == "__main__":
    main()
