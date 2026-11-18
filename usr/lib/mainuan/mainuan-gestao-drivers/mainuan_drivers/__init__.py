# SPDX-License-Identifier: GPL-2.0-or-later
"""Mainuan Gestao de Drivers application identity and resource locations."""
import gettext
from pathlib import Path

APP_NAME = "mainuan-gestao-drivers"
APP_ID = "org.mainuan.GestaoDrivers"
# Official product identity (package metadata, --version). The interface shows
# display_name(), whose Brazilian Portuguese translation is DISPLAY_NAME.
DISPLAY_NAME = "Gestão de Drivers"
ORGANIZATION = "Mainuan"
__version__ = "1.1"
VERSION = __version__

SHARE_DIR = Path(__file__).resolve().parents[4] / "share"
DATA_DIR = SHARE_DIR / "mainuan" / APP_NAME
LOCALE_DIR = SHARE_DIR / "locale"
ICON_PATH = SHARE_DIR / "icons/hicolor/scalable/apps" / (APP_NAME + ".svg")
ICON_PNG_PATH = SHARE_DIR / "icons/hicolor/48x48/apps" / (APP_NAME + ".png")


def display_name():
    """Return the localized application name for windows and dialogs."""
    # Translators: application name shown in the window title and menus.
    return gettext.dgettext(APP_NAME, "Driver Manager")
