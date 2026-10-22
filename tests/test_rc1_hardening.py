"""Release metadata and negative boundaries. Never use a mutating transport."""
import ast
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from mainuan_drivers import APP_NAME, DISPLAY_NAME, VERSION, __version__
from mainuan_drivers.backend.diagnostics import diagnostic_text
from mainuan_drivers.backend.models import AptOrigin
from mainuan_drivers.backend.transactions.execution import DriverExecutionController, SnapshotSource
from mainuan_drivers.backend.transactions.models import PackageReference, TransactionState
from mainuan_drivers.backend.transactions.packagekit import PackageKitTransaction
from mainuan_drivers.backend.transactions.planner import PlanningError
from mainuan_drivers.qt.main_window import MainWindow
from mainuan_drivers.qt.state import ViewState
from test_qt_frontend import app
from test_transaction_planner import scenario, target
from test_packagekit_transactions import FakeTransport
import test_qt_only_packaging as packaging_fixtures
from inspect_deb import PackageAuditError, audit_package

ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / "usr/lib/mainuan/mainuan-gestao-drivers/mainuan_drivers"


class ReleaseCandidateTests(unittest.TestCase):
    def test_version_alias_changelog_and_manpage(self):
        self.assertEqual(__version__, "1.0")
        self.assertEqual(VERSION, __version__)
        version = subprocess.run(["dpkg-parsechangelog", "-SVersion"], cwd=ROOT,
                                 check=True, text=True, capture_output=True).stdout.strip()
        self.assertEqual(version, __version__)
        self.assertIn('"Mainuan 1.0"', (ROOT / "usr/share/man/man1/mainuan-gestao-drivers.1").read_text())

    def test_debian_ordering_preserves_upgrade_and_final_release(self):
        for previous in ("0.4", "0.5", "0.6", "1.0~rc1"):
            with self.subTest(previous=previous):
                self.assertEqual(subprocess.run(["dpkg", "--compare-versions", previous, "lt", __version__]).returncode, 0)

    def test_about_and_diagnostics_share_release_version(self):
        app()
        window = MainWindow(test_mode=True, auto_start=False)
        self.addCleanup(window.deleteLater)
        self.addCleanup(window.close)
        with patch("mainuan_drivers.qt.main_window.QMessageBox.about") as about:
            window.show_about()
        self.assertEqual(about.call_args.args[2].splitlines()[0], DISPLAY_NAME + " " + __version__)
        self.assertEqual(json.loads(diagnostic_text(None, False, ViewState.LOADING))["version"], __version__)

    def test_version_and_help_exit_without_detection(self):
        launcher = ROOT / "usr/bin" / APP_NAME
        for flag in ("--version", "--help"):
            with self.subTest(flag=flag):
                result = subprocess.run([str(launcher), flag], capture_output=True, text=True, timeout=10,
                                        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                if flag == "--version":
                    self.assertEqual(result.stdout.strip(), DISPLAY_NAME + " " + __version__)
                else:
                    for option in ("--debug", "--version", "test"):
                        self.assertIn(option, result.stdout)

    def test_old_conffile_upgrade_limit_still_covers_04(self):
        text = (ROOT / "debian/mainuan-gestao-drivers.maintscript").read_text()
        self.assertIn(" 0.5~ " + APP_NAME, text)
        self.assertEqual(subprocess.run(["dpkg", "--compare-versions", "0.4", "le", "0.5~"]).returncode, 0)
        self.assertEqual(subprocess.run(["dpkg", "--compare-versions", "0.5", "gt", "0.5~"]).returncode, 0)

    def test_stable_workflow_and_gettext_version_match(self):
        workflow = (ROOT / ".github/workflows/build-mainuan-deb.yml").read_text()
        self.assertIn('test "$(dpkg-parsechangelog -SVersion)" = "1.0"', workflow)
        self.assertIn("mainuan-gestao-drivers_1.0_all.deb", workflow)
        self.assertIn("mainuan-gestao-drivers-1.0-${{ github.sha }}", workflow)
        self.assertNotIn("1.0~rc1", workflow)
        self.assertIn("--package-version='1.0'", (ROOT / "makepot").read_text())
        self.assertIn('Gestão de Drivers 1.0\\n', (ROOT / "mainuan-gestao-drivers.pot").read_text())
        self.assertIn('mainuan-gestao-drivers 1.0\\n', (ROOT / "po/mainuan-gestao-drivers-pt_BR.po").read_text())

    def test_stable_runtime_has_no_current_prerelease_labels(self):
        for path in MODULES.rglob("*.py"):
            with self.subTest(path=path.relative_to(MODULES)):
                text = path.read_text()
                self.assertNotIn("1.0~rc1", text)
                self.assertNotIn("Release candidate", text)
                self.assertNotIn("this beta", text)
                self.assertNotIn("This beta", text)


class PlanBoundaryTests(unittest.TestCase):
    def setUp(self):
        app()
        _, self.device, self.planner = scenario(True)
        self.plan = self.planner.build({self.device.device_id: target(self.device, "new-driver")})

    def test_malformed_selection_collection_returns_planning_error(self):
        for selections in (None, [], (None,), ("device",), (replace(self.plan.selections[0], device_id=[]),)):
            with self.subTest(selections=selections), self.assertRaises(PlanningError):
                self.planner.validate_plan(replace(self.plan, selections=selections))

    def test_unknown_device_and_option_of_another_device_are_rejected(self):
        _, other, _ = scenario(name="other-driver")
        for desired in ({"unknown": target(self.device, "new-driver")},
                        {self.device.device_id: target(other, "other-driver")}):
            with self.subTest(desired=desired), self.assertRaises(PlanningError):
                self.planner.build(desired)

    def test_arbitrary_package_id_or_modified_plan_never_reaches_dbus(self):
        bad_plans = (
            replace(self.plan, installs=(PackageReference("hello", "hello;1;amd64;"),)),
            replace(self.plan, installs=(replace(self.plan.installs[0], package_id="new-driver;999;amd64;"),)),
            replace(self.plan, removals=()),
            replace(self.plan, selections=(None,)),
            replace(self.plan, selections=(replace(self.plan.selections[0], device_id="unknown"),)),
        )
        for plan in bad_plans:
            for method in ("resolve", "install", "remove"):
                with self.subTest(plan=plan, method=method):
                    calls, results = [], []
                    transaction = PackageKitTransaction(self.planner, execution_enabled=True,
                        transport_factory=lambda parent: FakeTransport(parent, calls))
                    transaction.finished.connect(results.append)
                    getattr(transaction, method)(plan)
                    self.assertEqual(results[0].state, TransactionState.FAILED)
                    self.assertEqual(results[0].error.error_code, "invalid-plan")
                    self.assertEqual(calls, [])
                    transaction.deleteLater()

    def test_missing_prepared_plan_cannot_be_confirmed_or_discarded(self):
        controller = DriverExecutionController(test_mode=True)
        self.addCleanup(controller.deleteLater)
        finished = []
        controller.finished.connect(finished.append)
        for invalid in (None, object(), self.plan):
            self.assertFalse(controller.confirm(invalid))
            controller.discard(invalid)
        self.assertEqual(finished, [])
        self.assertFalse(controller.active)


class DiagnosticAndPayloadTests(unittest.TestCase):
    def test_diagnostic_origin_allowlist_does_not_export_new_attributes(self):
        snapshot = SnapshotSource(test_mode=True).load()
        device = snapshot.planner.devices[0]
        origin = AptOrigin("Vendor", "Graphics", "resolute", "example.invalid")
        # An added upstream/model attribute must not silently become exported.
        object.__setattr__(origin, "private_token", "secret-sentinel")
        option = replace(device.drivers[0], origins=(origin,))
        device = replace(device, drivers=(option,))
        snapshot = replace(snapshot, planner=type(snapshot.planner)((device,)))
        data = json.loads(diagnostic_text(snapshot, True, ViewState.READY_WITH_DRIVERS))
        exported = data["devices"][0]["drivers"][0]["origins"][0]
        self.assertEqual(set(exported), {"origin", "label", "archive", "site"})
        self.assertNotIn("secret-sentinel", json.dumps(data))

    def test_development_payload_is_rejected_even_outside_tests_directory(self):
        fixture = packaging_fixtures.QtOnlyPackagingTests()
        fixture.setUp()
        for path in ("usr/lib/.git/config", "usr/lib/.github/workflows/test.yml", "usr/tools/audit.sh",
                     "usr/lib/qt_ux_probe.py", "usr/lib/probe_packagekit_readonly.py", "usr/lib/inspect_deb.py",
                     "usr/share/Makefile", "usr/share/makepot", "usr/lib/archive.deb", "usr/lib/archive.buildinfo"):
            with self.subTest(path=path), self.assertRaises(PackageAuditError):
                audit_package(fixture.control, fixture.members + [packaging_fixtures.member(path)], fixture.scripts)

    def test_runtime_has_no_shell_execution_or_privilege_helpers(self):
        for path in MODULES.rglob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                for keyword in node.keywords:
                    if keyword.arg == "shell":
                        self.assertIsInstance(keyword.value, ast.Constant, str(path))
                        self.assertIs(keyword.value.value, False, str(path))
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    self.assertNotIn((node.func.value.id, node.func.attr),
                                     {("os", "system"), ("os", "popen"), ("subprocess", "getoutput"),
                                      ("subprocess", "getstatusoutput")}, str(path))


if __name__ == "__main__":
    unittest.main()
