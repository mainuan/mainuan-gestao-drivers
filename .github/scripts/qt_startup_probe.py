#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Child of cpu_smoke.py: exercise the packaged entry point with fixture I/O."""
import argparse
import json
import os
from pathlib import Path
import runpy
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--normal-entry", action="store_true")
    parser.add_argument("--emulator", type=Path)
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Startup tests must run as an unprivileged user")
    sys.path.insert(0, str(args.payload / "usr/lib/mainuan/mainuan-gestao-drivers"))
    # Import real distro native dependencies, without detecting hardware or
    # starting a transaction. These must also work under the constrained CPU.
    import apt
    import apt_pkg
    import UbuntuDrivers.detect
    from PyQt6 import QtDBus
    from PyQt6.QtCore import QTimer, QT_VERSION_STR, PYQT_VERSION_STR
    from PyQt6.QtWidgets import QApplication, QRadioButton
    import mainuan_drivers
    assert Path(mainuan_drivers.__file__).resolve().is_relative_to(args.payload.resolve())
    from mainuan_drivers.qt import application
    from mainuan_drivers.backend.transactions.packagekit import QtDBusTransport, PackageKitTransaction

    def forbidden(*unused, **kwargs):
        raise AssertionError("D-Bus/mutation forbidden in the CPU startup probe")
    QtDBusTransport.call = forbidden
    PackageKitTransaction.install = forbidden
    PackageKitTransaction.remove = forbidden
    if args.normal_entry:
        # Check the no-argument Welcome integration, injecting only fixture I/O
        # instead of probing host hardware/firmware or the system bus.
        from mainuan_drivers.qt.main_window import MainWindow
        from mainuan_drivers.backend.transactions.execution import DriverExecutionController
        def normal_window(test_mode=False):
            assert not test_mode
            window = MainWindow(auto_start=False, executor=DriverExecutionController(test_mode=True))
            window.refresh()
            return window
        application.MainWindow = normal_window
    original_exec = QApplication.exec
    result = {}

    def checked_exec():
        app = QApplication.instance()
        def ready():
            windows = [window for window in app.topLevelWidgets() if hasattr(window, "_thread")]
            if not windows or any(window._thread is not None for window in windows):
                QTimer.singleShot(50, ready)
                return
            try:
                assert app.platformName() == "offscreen"
                assert not app.windowIcon().isNull()
                assert not app.windowIcon().pixmap(48, 48).isNull()
                window = windows[0]
                assert window._snapshot is not None and window._snapshot.planner.devices
                assert window.findChildren(QRadioButton)
                assert not window.grab().isNull()
                assert not window.executor.active
                blocked = {"gi", "Gtk", "Gdk", "GdkPixbuf", "XApp", "GLib", "Gio", "PackageKitGlib"}
                assert not any(set(name.split(".")) & blocked for name in sys.modules)
                paths = set()
                for line in Path("/proc/self/maps").read_text().splitlines():
                    fields = line.split(maxsplit=5)
                    if len(fields) != 6 or not fields[5].startswith("/"):
                        continue
                    path = Path(fields[5])
                    if args.emulator and path.resolve() == args.emulator.resolve():
                        continue
                    if path.is_file():
                        with path.open("rb") as stream:
                            if stream.read(4) == b"\x7fELF":
                                paths.add(str(path.resolve()))
                for expected in ("libQt6Widgets.so", "libQt6DBus.so", "apt_pkg."):
                    assert any(expected in path for path in paths), expected
                result.update(success=True, mode="normal-entry-fixture-io" if args.normal_entry else "test-entry",
                              version=app.applicationVersion(), platform=app.platformName(), icon_valid=True,
                              qt=QT_VERSION_STR, pyqt=PYQT_VERSION_STR, python=sys.version,
                              packaged_module=str(Path(mainuan_drivers.__file__).relative_to(args.payload)),
                              loaded_elf=sorted(paths), devices=len(window._snapshot.planner.devices))
                for window in windows:
                    window.close()
                app.quit()
            except Exception as error:
                result.update(success=False, error=str(error))
                app.exit(1)
        QTimer.singleShot(0, ready)
        return original_exec()
    QApplication.exec = staticmethod(checked_exec)
    sys.argv = ["mainuan-gestao-drivers"] + ([] if args.normal_entry else ["test"])
    try:
        runpy.run_path(str(args.payload / "usr/bin/mainuan-gestao-drivers"), run_name="__main__")
    except SystemExit as exit_status:
        if exit_status.code not in (0, None):
            raise
    if not result.get("success"):
        raise RuntimeError("Packaged startup failed: " + str(result))
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("PASS: packaged Qt startup and safe shutdown:", result["mode"], result["version"], flush=True)


if __name__ == "__main__":
    main()
