from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSlider, QLabel
from PyQt6.QtCore import Qt, QEvent, pyqtSignal
from PyQt6.QtGui import QIcon


class ControlBar(QWidget):
    playback_toggled = pyqtSignal()
    volume_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        self._play_stop_btn = QPushButton(QIcon.fromTheme("media-playback-stop"), "Stop")
        self._play_stop_btn.setFlat(True)
        self._play_stop_btn.clicked.connect(self.playback_toggled)
        layout.addWidget(self._play_stop_btn)

        layout.addStretch()

        self._vol_icon = QLabel()
        self._vol_icon.setPixmap(QIcon.fromTheme("audio-volume-medium").pixmap(16, 16))
        layout.addWidget(self._vol_icon)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(80)
        self._slider.setFixedWidth(140)
        self._slider.valueChanged.connect(self.volume_changed)
        layout.addWidget(self._slider)

    def set_playing(self, playing: bool):
        if playing:
            self._play_stop_btn.setIcon(QIcon.fromTheme("media-playback-stop"))
            self._play_stop_btn.setText("Stop")
        else:
            self._play_stop_btn.setIcon(QIcon.fromTheme("media-playback-start"))
            self._play_stop_btn.setText("Play")

    def set_volume_slider(self, value: int):
        self._slider.blockSignals(True)
        self._slider.setValue(value)
        self._slider.blockSignals(False)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.PaletteChange:
            self._vol_icon.setPixmap(QIcon.fromTheme("audio-volume-medium").pixmap(16, 16))
        super().changeEvent(event)

    @property
    def volume(self) -> int:
        return self._slider.value()
