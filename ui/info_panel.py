from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QApplication
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QIcon, QPalette, QPixmap, QDesktopServices


class InfoPanel(QWidget):
    favourite_toggled = pyqtSignal(str, bool)  # uuid, new state

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self._uuid = ""
        self._station_name = ""
        self._homepage_url = ""

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

        self._name = QLabel()
        self._name.setWordWrap(True)
        f = self._name.font()
        f.setBold(True)
        self._name.setFont(f)
        layout.addWidget(self._name)

        self._country = self._muted_label()
        layout.addWidget(self._country)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 2, 0, 0)
        btn_row.setSpacing(2)

        self._copy_name_btn = self._copy_button()
        self._copy_name_btn.setEnabled(False)
        self._copy_name_btn.setToolTip(self.tr("Copy station name"))
        self._copy_name_btn.clicked.connect(lambda: QApplication.clipboard().setText(self._station_name))
        btn_row.addWidget(self._copy_name_btn)

        self._homepage_btn = QPushButton()
        self._homepage_btn.setFlat(True)
        self._homepage_btn.setFixedSize(20, 20)
        self._homepage_btn.setToolTip(self.tr("Open station website"))
        self._homepage_btn.setEnabled(False)
        self._homepage_btn.hide()
        _home_icon = QIcon.fromTheme("go-home")
        if _home_icon.isNull():
            self._homepage_btn.setText("🏠")
        else:
            self._homepage_btn.setIcon(_home_icon)
        self._homepage_btn.clicked.connect(self._open_homepage)
        btn_row.addWidget(self._homepage_btn)

        self._info_btn = QPushButton()
        self._info_btn.setFlat(True)
        self._info_btn.setFixedSize(20, 20)
        self._info_btn.setToolTip(self.tr("Open on radio-browser.info"))
        self._info_btn.setEnabled(False)
        self._info_btn.hide()
        _info_icon = QIcon.fromTheme("web-browser")
        if _info_icon.isNull():
            self._info_btn.setText("↗")
        else:
            self._info_btn.setIcon(_info_icon)
        self._info_btn.clicked.connect(self._open_info_url)
        btn_row.addWidget(self._info_btn)

        self._fav_btn = QPushButton()
        self._fav_btn.setFlat(True)
        self._fav_btn.setFixedSize(24, 24)
        self._fav_btn.setCheckable(True)
        self._fav_btn.setEnabled(False)
        self._update_heart(False)
        self._fav_btn.toggled.connect(self._on_fav_toggled)
        btn_row.addWidget(self._fav_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        self._now_playing_text = ""
        now_row = QHBoxLayout()
        now_row.setContentsMargins(0, 0, 0, 0)
        now_row.setSpacing(4)
        self._now_playing = QLabel()
        self._now_playing.setWordWrap(True)
        now_row.addWidget(self._now_playing, 1)
        self._copy_song_btn = self._copy_button()
        self._copy_song_btn.setToolTip(self.tr("Copy song info"))
        self._copy_song_btn.clicked.connect(lambda: QApplication.clipboard().setText(self._now_playing_text))
        now_row.addWidget(self._copy_song_btn, 0, Qt.AlignmentFlag.AlignTop)
        self._now_playing_row = QWidget()
        self._now_playing_row.setLayout(now_row)
        self._now_playing_row.hide()
        layout.addWidget(self._now_playing_row)

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
        self._station_name = station.get("name", "")
        self._homepage_url = station.get("homepage", "")
        self._name.setText(self._station_name)
        self._country.setText(station.get("country", ""))
        is_custom = bool(station.get("custom"))
        self._fav_btn.setVisible(not is_custom)
        self._fav_btn.setEnabled(not is_custom)
        has_homepage = bool(self._homepage_url) and not is_custom
        self._homepage_btn.setVisible(has_homepage)
        self._homepage_btn.setEnabled(has_homepage)
        self._info_btn.setVisible(not is_custom)
        self._info_btn.setEnabled(not is_custom)
        self._copy_name_btn.setEnabled(True)
        if not is_custom:
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

        self._now_playing_row.hide()
        self._now_playing.clear()
        self._now_playing_text = ""

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
            self._now_playing_text = title
            self._now_playing.setText(title)
            self._now_playing_row.show()
        else:
            self._now_playing_row.hide()
            self._now_playing_text = ""

    def set_favourite(self, is_fav: bool):
        self._fav_btn.blockSignals(True)
        self._fav_btn.setChecked(is_fav)
        self._fav_btn.blockSignals(False)
        self._update_heart(is_fav)

    def _open_homepage(self):
        if self._homepage_url:
            QDesktopServices.openUrl(QUrl(self._homepage_url))

    def _open_info_url(self):
        if self._uuid:
            QDesktopServices.openUrl(QUrl(f"https://www.radio-browser.info/history/{self._uuid}"))

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
    def _copy_button() -> QPushButton:
        btn = QPushButton()
        btn.setFlat(True)
        btn.setFixedSize(20, 20)
        icon = QIcon.fromTheme("edit-copy")
        if icon.isNull():
            btn.setText("⧉")
        else:
            btn.setIcon(icon)
        return btn

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
