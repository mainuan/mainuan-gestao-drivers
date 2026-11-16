"""Runtime i18n: the interface follows LANGUAGE, English is the source language."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "usr/lib/mainuan/mainuan-gestao-drivers"
DOMAIN = "mainuan-gestao-drivers"

CHECK = r'''
import gettext, sys
sys.path.insert(0, sys.argv[1])
from PyQt6.QtWidgets import QApplication
from mainuan_drivers.qt import application
from mainuan_drivers.qt.main_window import MainWindow, execution_message
from mainuan_drivers.backend.transactions.planner import TransactionPlanner, PlanningError
from mainuan_drivers import APP_NAME, display_name
gettext.bindtextdomain(APP_NAME, sys.argv[2])  # freshly compiled catalogs
app = QApplication([APP_NAME])
window = MainWindow(test_mode=False, auto_start=False)
try:
    TransactionPlanner([]).validate_plan(None)
except PlanningError as error:
    planning = str(error)
print(window.windowTitle())
print(display_name())
print(window.refresh_button.text())
print(planning)
'''

# Runs the real application.run() with an empty Qt translations directory
# (no qtbase_<lang>.qm) and reports the resulting layout direction.
DIRECTION_CHECK = r'''
import gettext, sys, tempfile
from unittest import mock
sys.path.insert(0, sys.argv[1])
from PyQt6.QtWidgets import QApplication
from mainuan_drivers.qt import application
from mainuan_drivers.qt.main_window import MainWindow
from mainuan_drivers import APP_NAME
gettext.bindtextdomain(APP_NAME, sys.argv[2])  # freshly compiled catalogs

def fake_exec(app):
    windows = [w for w in app.topLevelWidgets() if isinstance(w, MainWindow)]
    print(app.layoutDirection().name, [w.isRightToLeft() for w in windows], windows[0].refresh_button.text())
    return 0

with tempfile.TemporaryDirectory() as empty, \
        mock.patch.object(application.QLibraryInfo, "path", return_value=empty), \
        mock.patch.object(QApplication, "exec", fake_exec), \
        mock.patch.object(application, "MainWindow",
                          lambda test_mode: MainWindow(test_mode=test_mode, auto_start=False)):
    application.run([APP_NAME])
'''


class RuntimeTranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.localedir = Path(cls._tmp.name)
        target = cls.localedir / "pt_BR/LC_MESSAGES"
        target.mkdir(parents=True)
        subprocess.run(["msgfmt", "--check", "-o", str(target / (DOMAIN + ".mo")),
                        str(ROOT / "po" / (DOMAIN + "-pt_BR.po"))], check=True)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def run_ui(self, language):
        env = {key: value for key, value in os.environ.items()
               if key not in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")}
        env.update({"QT_QPA_PLATFORM": "offscreen", "LANGUAGE": language, "LANG": "C.UTF-8"})
        result = subprocess.run([sys.executable, "-c", CHECK, str(MODULE_PATH), str(self.localedir)],
                                env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.splitlines()

    def test_brazilian_portuguese_shows_the_original_interface(self):
        self.assertEqual(self.run_ui("pt_BR"), ["Gestão de Drivers", "Gestão de Drivers", "Atualizar",
                                               "É necessário um plano de transação de drivers"])

    def test_english_and_c_show_the_source_strings(self):
        for language in ("en", "C", "xx"):
            with self.subTest(language=language):
                self.assertEqual(self.run_ui(language), ["Driver Manager", "Driver Manager", "Refresh",
                                                        "A driver transaction plan is required"])

    def run_direction(self, language):
        env = {key: value for key, value in os.environ.items()
               if key not in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")}
        env.update({"QT_QPA_PLATFORM": "offscreen", "LANGUAGE": language, "LANG": "C.UTF-8"})
        result = subprocess.run([sys.executable, "-c", DIRECTION_CHECK, str(MODULE_PATH), str(self.localedir)],
                                env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.splitlines()[-1]

    def test_right_to_left_catalog_mirrors_without_qtbase(self):
        for language in ("ar", "ur"):
            target = self.localedir / language / "LC_MESSAGES"
            target.mkdir(parents=True, exist_ok=True)
            subprocess.run(["msgfmt", "--check", "-o", str(target / (DOMAIN + ".mo")),
                            str(ROOT / "po" / (DOMAIN + "-" + language + ".po"))], check=True)
        # The application's own Arabic and Urdu catalogs are used: mirrored even
        # without qtbase (there is no qtbase_ur at all).
        for language in ("ar", "ur"):
            with self.subTest(language=language):
                self.assertTrue(self.run_direction(language).startswith("RightToLeft [True] "))
        # Yiddish is right-to-left but has no application catalog: English, left to right.
        self.assertEqual(self.run_direction("yi"), "LeftToRight [False] Refresh")

    def test_brazilian_catalog_is_complete(self):
        stats = subprocess.run(["msgfmt", "--statistics", "-o", os.devnull,
                                str(ROOT / "po" / (DOMAIN + "-pt_BR.po"))],
                               capture_output=True, text=True, env={**os.environ, "LC_ALL": "C"}, check=True)
        self.assertNotIn("untranslated", stats.stderr)
        self.assertNotIn("fuzzy", stats.stderr)

    def test_language_is_never_forced(self):
        for path in (MODULE_PATH / "mainuan_drivers").rglob("*.py"):
            text = path.read_text()
            self.assertNotIn("QLocale.setDefault", text, str(path))
            self.assertNotRegex(text, r"environ\[[\"'](LANGUAGE|LANG|LC_ALL|LC_MESSAGES)", str(path))
        self.assertNotIn("LANG=", (ROOT / "data/org.mainuan.GestaoDrivers.desktop.in").read_text())


if __name__ == "__main__":
    unittest.main()
