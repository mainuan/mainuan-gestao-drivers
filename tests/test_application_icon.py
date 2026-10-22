"""Exercise real Qt icon engines in fresh processes, including missing SVG."""
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "usr/lib/mainuan/mainuan-gestao-drivers"

SETUP = r'''
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from PyQt6.QtCore import QCoreApplication, QLibraryInfo, QTimer, Qt
from PyQt6.QtGui import QColor, QIcon, QImageReader, QPixmap
from PyQt6.QtWidgets import QApplication
from mainuan_drivers import APP_NAME, ICON_PATH, ICON_PNG_PATH
from mainuan_drivers.qt import application
temporary = tempfile.TemporaryDirectory()
root = Path(temporary.name)
if sys.argv[2] == 'no-svg':
    plugins = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath))
    (root / 'platforms').mkdir()
    (root / 'platforms/libqoffscreen.so').symlink_to(plugins / 'platforms/libqoffscreen.so')
    QCoreApplication.setLibraryPaths([str(root)])
QIcon.setThemeSearchPaths([])
QIcon.setFallbackSearchPaths([])
QIcon.setThemeName('mainuan-icon-test-no-theme')
QIcon.setFallbackThemeName('')
'''


class ApplicationIconTests(unittest.TestCase):
    def run_check(self, code, *, no_svg=False):
        result = subprocess.run(
            [sys.executable, "-c", SETUP + textwrap.dedent(code), str(MODULE_PATH),
             "no-svg" if no_svg else "normal"],
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
            capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_svg_is_renderable_with_declared_runtime_plugin(self):
        self.run_check('''
            app = QApplication([])
            assert ICON_PATH.is_file()
            assert QImageReader(str(ICON_PATH)).canRead()
            svg = QIcon(str(ICON_PATH))
            assert not svg.isNull()
            assert not svg.pixmap(48, 48).isNull()
            # With no theme, the scalable artwork is preferred over the PNG.
            assert application.application_icon().pixmap(48, 48).toImage() == svg.pixmap(48, 48).toImage()
        ''')

    def test_official_png_fallback_without_any_svg_plugin(self):
        self.run_check('''
            app = QApplication([])
            assert b'svg' not in QImageReader.supportedImageFormats()
            assert QIcon(str(ICON_PATH)).isNull()
            png = QIcon(str(ICON_PNG_PATH))
            assert ICON_PNG_PATH.is_file()
            assert not png.isNull()
            assert not png.pixmap(48, 48).isNull()
            icon = application.application_icon()
            assert not icon.isNull()
            assert icon.pixmap(48, 48).toImage() == png.pixmap(48, 48).toImage()
        ''', no_svg=True)

    def test_user_theme_takes_precedence_over_bundled_artwork(self):
        self.run_check('''
            app = QApplication([])
            theme = root / 'theme'
            icons = theme / '48x48/apps'
            icons.mkdir(parents=True)
            (theme / 'index.theme').write_text(
                '[Icon Theme]\\nName=Icon test\\nDirectories=48x48/apps\\n'
                '[48x48/apps]\\nSize=48\\nType=Fixed\\nContext=Applications\\n')
            pixmap = QPixmap(48, 48)
            pixmap.fill(QColor(Qt.GlobalColor.red))
            assert pixmap.save(str(icons / (APP_NAME + '.png')))
            QIcon.setThemeSearchPaths([str(root)])
            QIcon.setThemeName('theme')
            assert QIcon.hasThemeIcon(APP_NAME)
            assert application.application_icon().pixmap(48, 48).toImage() == pixmap.toImage()
        ''')

    def test_full_application_keeps_nonnull_icon_without_svg(self):
        self.run_check('''
            factory = application.QApplication
            def create(argv):
                app = factory(argv)
                QTimer.singleShot(0, app.quit)
                return app
            def window(test_mode=False):
                result = application_window(test_mode=test_mode, auto_start=False)
                assert not QApplication.windowIcon().isNull()
                assert not QApplication.windowIcon().pixmap(48, 48).isNull()
                return result
            application_window = application.MainWindow
            application.QApplication = create
            application.MainWindow = window
            assert application.run([APP_NAME]) == 0
        ''', no_svg=True)
