from pathlib import Path
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon

_ICON      = str(Path(__file__).parent.parent / "assets" / "icons" / "dyedfox-radio.png")
_ICON_TRAY = str(Path(__file__).parent.parent / "assets" / "icons" / "dyedfox-radio-tray.svg")


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, window, backend, parent=None):
        super().__init__(QIcon(_ICON_TRAY), parent)
        self._window = window
        self._backend = backend
        self._build_menu()
        self.activated.connect(self._on_activate)
        self.setToolTip("Dyedfox Radio")

        backend.playback_started.connect(lambda: self._set_playing(True))
        backend.playback_stopped.connect(lambda: self._set_playing(False))

    def _build_menu(self):
        menu = QMenu()
        self._action_show = menu.addAction("Show / Hide")
        self._action_show.triggered.connect(self._toggle_window)
        menu.addSeparator()
        self._action_playstop = menu.addAction("Play")
        self._action_playstop.triggered.connect(self._toggle_playback)
        menu.addSeparator()
        menu.addAction("Quit").triggered.connect(QApplication.quit)
        self.setContextMenu(menu)

    def _set_playing(self, playing: bool):
        self._action_playstop.setText("Stop" if playing else "Play")

    def _toggle_playback(self):
        if self._backend.is_playing:
            self._backend.stop()
        else:
            self._backend.play_last()

    def _on_activate(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            self._toggle_playback()
        elif reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._toggle_window()

    def _toggle_window(self):
        if self._window.isVisible():
            self._window.hide()
        else:
            self._window.show()
            self._window.raise_()
            self._window.activateWindow()

    def update_status(self, station: str, song: str):
        if song:
            self.setToolTip(f"Dyedfox Radio  —  {station}  —  {song}")
        else:
            self.setToolTip(f"Dyedfox Radio  —  {station}")
