from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPalette, QPixmap


class InfoPanel(QWidget):
    favourite_toggled = pyqtSignal(str, bool)  # uuid, new state

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self._uuid = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._logo = QLabel()
        self._logo.setFixedSize(184, 184)
        self._logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo.setStyleSheet(
            "QLabel { background: palette(mid); border-radius: 6px; }"
        )
        self._logo.setPixmap(QIcon.fromTheme("audio-x-generic").pixmap(48, 48))
        layout.addWidget(self._logo)

        layout.addSpacing(4)

        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(4)

        self._name = QLabel()
        self._name.setWordWrap(True)
        f = self._name.font()
        f.setBold(True)
        self._name.setFont(f)
        name_row.addWidget(self._name, 1)

        self._fav_btn = QPushButton()
        self._fav_btn.setFlat(True)
        self._fav_btn.setFixedSize(24, 24)
        self._fav_btn.setCheckable(True)
        self._fav_btn.setEnabled(False)
        self._update_heart(False)
        self._fav_btn.toggled.connect(self._on_fav_toggled)
        name_row.addWidget(self._fav_btn, 0, Qt.AlignmentFlag.AlignTop)

        layout.addLayout(name_row)

        self._country = self._muted_label()
        layout.addWidget(self._country)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        self._now_playing = QLabel()
        self._now_playing.setWordWrap(True)
        self._now_playing.hide()
        layout.addWidget(self._now_playing)

        self._bitrate = self._muted_label()
        layout.addWidget(self._bitrate)

        self._language = self._muted_label()
        layout.addWidget(self._language)

        self._tags = self._muted_label()
        self._tags.setWordWrap(True)
        layout.addWidget(self._tags)

        self._votes = self._muted_label()
        layout.addWidget(self._votes)

        layout.addStretch()

    def set_station(self, station: dict, is_favourite: bool = False):
        self._uuid = station.get("stationuuid", "")
        self._name.setText(station.get("name", ""))
        self._country.setText(station.get("country", ""))
        self._fav_btn.setEnabled(True)
        self.set_favourite(is_favourite)

        bitrate = station.get("bitrate", 0)
        codec = station.get("codec", "")
        parts = [p for p in [codec, f"{bitrate} kbps" if bitrate else ""] if p]
        self._bitrate.setText("  ·  ".join(parts))

        self._language.setText(station.get("language", ""))

        raw_tags = station.get("tags", "")
        tag_list = [t.strip() for t in raw_tags.split(",") if t.strip()]
        self._tags.setText(", ".join(tag_list[:8]))

        votes = station.get("votes", 0)
        self._votes.setText(f"▲ {votes:,}" if votes else "")

        self._now_playing.hide()
        self._now_playing.clear()

        favicon_url = station.get("favicon", "")
        if favicon_url:
            self._logo.setPixmap(QIcon.fromTheme("audio-x-generic").pixmap(48, 48))
        else:
            self._logo.setPixmap(QIcon.fromTheme("audio-x-generic").pixmap(48, 48))

    def set_favicon(self, data: bytes):
        pix = QPixmap()
        pix.loadFromData(data)
        if not pix.isNull():
            self._logo.setPixmap(
                pix.scaled(184, 184, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )

    def set_now_playing(self, title: str):
        if title:
            self._now_playing.setText(title)
            self._now_playing.show()
        else:
            self._now_playing.hide()

    def set_favourite(self, is_fav: bool):
        self._fav_btn.blockSignals(True)
        self._fav_btn.setChecked(is_fav)
        self._fav_btn.blockSignals(False)
        self._update_heart(is_fav)

    def _on_fav_toggled(self, checked: bool):
        self._update_heart(checked)
        if self._uuid:
            self.favourite_toggled.emit(self._uuid, checked)

    def _update_heart(self, is_fav: bool):
        icon = QIcon.fromTheme("emblem-favorite" if is_fav else "emblem-favorite-symbolic")
        if icon.isNull():
            self._fav_btn.setText("♥" if is_fav else "♡")
            self._fav_btn.setIcon(QIcon())
        else:
            self._fav_btn.setText("")
            self._fav_btn.setIcon(icon)

    @staticmethod
    def _muted_label() -> QLabel:
        label = QLabel()
        p = label.palette()
        p.setColor(
            QPalette.ColorRole.WindowText,
            label.palette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText),
        )
        label.setPalette(p)
        return label
