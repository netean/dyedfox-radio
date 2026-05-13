import os
import sys

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

# Must be called before QApplication and any dbus connection.
try:
    import dbus.mainloop.glib
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
except ImportError:
    pass

from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon

from player.backend import GStreamerBackend
from player.mpris import setup_mpris
from api.radio_browser import RadioBrowserClient
from data.favourites import FavouritesManager, RecentManager
from data.settings import Settings
from tray.tray_icon import SystemTrayIcon
from ui.main_window import MainWindow


def main():
    Gst.init(None)

    # Load settings before QApplication so we can suppress the KDE startup
    # notification when starting minimized. Qt reads DESKTOP_STARTUP_ID in
    # QApplication.__init__; removing it beforehand prevents KDE from showing
    # a launcher indicator that would linger alongside the tray icon.
    settings = Settings()
    if settings["start_minimized"]:
        os.environ.pop("DESKTOP_STARTUP_ID", None)

    app = QApplication(sys.argv)
    app.setApplicationName("Dyedfox Radio")
    app.setDesktopFileName("dyedfox-radio")
    app.setQuitOnLastWindowClosed(False)

    _icon_path = str(Path(__file__).parent / "assets" / "icons" / "dyedfox-radio.png")
    app.setWindowIcon(QIcon(_icon_path))

    favourites = FavouritesManager()
    recent = RecentManager()
    backend = GStreamerBackend()
    api = RadioBrowserClient()

    window = MainWindow(backend, api, favourites, recent, settings)

    tray = SystemTrayIcon(window, backend)
    QTimer.singleShot(0, tray.show)
    window.set_tray(tray)

    mpris = setup_mpris(backend, window)
    window.set_mpris(mpris)

    if not settings["start_minimized"]:
        window.show()

    autoplay_uuid = recent.uuids()[0] if settings["autoplay_last"] and recent.uuids() else ""
    window.load_top_stations(autoplay_uuid=autoplay_uuid)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
