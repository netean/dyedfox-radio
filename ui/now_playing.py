from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPalette


class _ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full = text
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        super().setText(text)

    def setText(self, text: str):
        self._full = text
        self._elide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._elide()

    def _elide(self):
        w = self.width()
        if w <= 0:
            super().setText(self._full)
            return
        super().setText(self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideRight, w))


class NowPlayingBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self._station = ""
        self._song = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        self._icon = QLabel()
        self._icon.setPixmap(QIcon.fromTheme("audio-x-generic").pixmap(20, 20))
        self._icon.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._icon)

        self._label = _ElidedLabel(self.tr("Not playing"))
        layout.addWidget(self._label, 1)

    def set_station(self, name: str):
        self._station = name
        self._song = ""
        self._update()

    def set_song(self, title: str):
        self._song = title
        self._update()

    def clear_song(self):
        self._song = ""
        self._update()

    def set_error(self):
        self._song = self.tr("Stream unavailable")
        self._update()

    def _update(self):
        if self._song:
            self._label.setText(f"{self._station}  —  {self._song}")
        else:
            self._label.setText(self._station or self.tr("Not playing"))
