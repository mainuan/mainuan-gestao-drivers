#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Extract, never install, the Python .deb and start Qt offscreen safely.

Default: QEMU baseline gate. --native is inventory/startup only, not CPU proof.
No compiler, test ELF or native library is added to the application package.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

CPU = "qemu64,-sse3,-cx16,-lahf-lm,-ssse3,-sse4.1,-sse4.2,-popcnt,-avx,-avx2,-avx512f,-fma,-f16c,-bmi1,-bmi2,-abm"
LOADER = "/lib64/ld-linux-x86-64.so.2"


def verify_diagnostics(text):
    """glibc 2.43 diagnostics adapter, fail closed if fields/layout change."""
    def value(key):
        match = re.search(r"^" + re.escape(key) + r"=(0x[0-9a-f]+)$", text, re.M)
        if not match:
            raise ValueError("Missing glibc CPU diagnostic: " + key)
        return int(match[1], 16)
    if value("dl_hwcaps_subdirs_active") != 0:
        raise ValueError("QEMU still exposes an x86-64-v2/v3/v4 hwcaps level")
    leaf1 = "x86.cpu_features.features[0x0].cpuid"
    if not value(leaf1 + "[0x3]") & (1 << 26):
        raise ValueError("SSE2 is missing")
    if value(leaf1 + "[0x2]") & sum(1 << bit for bit in (0, 9, 12, 13, 19, 20, 23, 28, 29)):
        raise ValueError("Post-baseline SSE/AVX/POPCNT/CX16 features are exposed")
    if value("x86.cpu_features.features[0x1].cpuid[0x1]") & sum(1 << bit for bit in (3, 5, 8, 16)):
        raise ValueError("BMI/AVX2/AVX512 features are exposed")
    if value("x86.cpu_features.features[0x2].cpuid[0x2]") & ((1 << 0) | (1 << 5)):
        raise ValueError("LAHF/LZCNT features are exposed")


def run(argv, env, echo=True):
    result = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=120)
    if echo:
        print(result.stdout, end="", flush=True)
    print(result.stderr, end="", flush=True)
    if result.returncode or "CPU ISA level is lower than required" in result.stdout + result.stderr:
        raise ValueError("Startup/loader failed, exit %s" % result.returncode)
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--qemu", default="qemu-x86_64")
    parser.add_argument("--native", action="store_true", help="No emulation: explicitly NOT evidence of baseline CPU execution")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Do not run startup/packaging validation as root")
    qemu = None if args.native else shutil.which(args.qemu)
    if not args.native and not qemu:
        parser.error("QEMU is mandatory for the baseline gate; --native is only a separate host smoke")
    try:
        # Reuse the package gate, including native-payload rejection, before extraction.
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests"))
        from inspect_deb import inspect_deb
        inspect_deb(args.package)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "package"
            subprocess.run(["dpkg-deb", "-x", str(args.package.resolve()), str(payload)], check=True)
            env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C.UTF-8", "QT_QPA_PLATFORM": "offscreen",
                   "PYTHONDONTWRITEBYTECODE": "1", "LIBGL_ALWAYS_SOFTWARE": "1"}
            for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_RUNTIME_DIR"):
                folder = root / key
                folder.mkdir(mode=0o700)
                env[key] = str(folder)
            prefix = [qemu, "-cpu", CPU] if qemu else []
            diagnostics = run([*prefix, LOADER, "--list-diagnostics"], env, echo=False)
            # Never export loader env/auxv/uname diagnostics: only CPU evidence.
            diagnostics = "\n".join(line for line in diagnostics.splitlines()
                                    if line.startswith(("x86.cpu_features.", "dl_hwcaps_subdirs_active=")))
            if qemu:
                verify_diagnostics(diagnostics)
            runs = []
            child = Path(__file__).with_name("qt_startup_probe.py").resolve()
            for mode in ("test", "normal"):
                output = root / (mode + ".json")
                command = [*prefix, str(Path("/usr/bin/python3").resolve()), "-B", str(child), str(payload), "--output", str(output)]
                if mode == "normal":
                    command.append("--normal-entry")
                if qemu:
                    command.extend(["--emulator", qemu])
                run(command, env)
                runs.append(json.loads(output.read_text()))
            report = {"baseline_emulated": bool(qemu), "cpu": CPU if qemu else "host CPU, NOT baseline proof",
                      "diagnostics": diagnostics, "runs": runs,
                      "limits": "User-mode emulation shares the host kernel; no ISO/Wayland/hardware/driver mutation test."}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print("PASS:", report["cpu"], "packaged Qt UI created and closed; no driver mutations")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, "CPU startup failed: %s\n" % error)


if __name__ == "__main__":
    main()
