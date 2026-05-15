import math
import requests
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QLabel, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize, QTimer, QRunnable, QObject, pyqtSignal, QThreadPool
from PyQt6.QtGui import QIcon, QPalette, QPixmap, QPainter

from data.favourites import FavouritesManager


class _WaveWidget(QWidget):
    """Animated 3-bar equalizer shown while a station is playing."""

    _BAR_PHASES = [0.0, 1.3, 2.6]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self._tick = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)

    def start(self):
        self._timer.start(60)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _step(self):
        self._tick += 1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.palette().color(QPalette.ColorRole.Highlight))

        w, h = self.width(), self.height()
        bar_w, gap, n = 4, 3, 3
        x0 = (w - (n * bar_w + (n - 1) * gap)) // 2
        t = self._tick * 0.22

        for i in range(n):
            amp = 0.5 + 0.5 * math.sin(t + self._BAR_PHASES[i])
            bar_h = max(4, int(4 + amp * (h - 10)))
            x = x0 + i * (bar_w + gap)
            y = (h - bar_h) // 2
            painter.drawRoundedRect(x, y, bar_w, bar_h, 2, 2)

        painter.end()


class _ElidedLabel(QLabel):
    """QLabel that truncates text with … instead of forcing the widget wider."""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        super().setText(text)

    def setText(self, text: str):
        self._full_text = text
        self._elide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._elide()

    def _elide(self):
        w = self.width()
        if w <= 0:
            super().setText(self._full_text)
            return
        super().setText(self.fontMetrics().elidedText(self._full_text, Qt.TextElideMode.ElideRight, w))


class _FaviconSignals(QObject):
    loaded = pyqtSignal(str, bytes)  # uuid, raw bytes


class _FaviconLoader(QRunnable):
    def __init__(self, uuid: str, url: str):
        super().__init__()
        self.setAutoDelete(True)
        self._uuid = uuid
        self._url = url
        self.signals = _FaviconSignals()

    def run(self):
        try:
            resp = requests.get(self._url, timeout=5, headers={"User-Agent": "RadioX/1.0"})
            if resp.ok and resp.content:
                self.signals.loaded.emit(self._uuid, resp.content)
        except Exception:
            pass


class StationRowWidget(QWidget):
    play_requested = pyqtSignal(dict)
    favourite_toggled = pyqtSignal(str, bool)  # uuid, new state

    def __init__(self, station: dict, favourites: FavouritesManager, parent=None, on_delete=None, on_edit=None):
        super().__init__(parent)
        self._station = station
        uuid = station.get("stationuuid", "")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        icon_box = QWidget()
        icon_box.setFixedSize(30, 30)
        self._favicon = QLabel(icon_box)
        self._favicon.setFixedSize(30, 30)
        self._favicon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._favicon.setPixmap(QIcon.fromTheme("audio-x-generic").pixmap(28, 28))
        self._wave = _WaveWidget(icon_box)
        self._wave.hide()
        layout.addWidget(icon_box)

        text = QWidget()
        text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        text_layout = QVBoxLayout(text)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        name_label = _ElidedLabel(station.get("name", ""))
        f = name_label.font()
        f.setBold(True)
        name_label.setFont(f)
        name_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        text_layout.addWidget(name_label)

        tags = [t.strip() for t in station.get("tags", "").split(",") if t.strip()]
        first_tag = tags[0] if tags else ""
        bitrate = station.get("bitrate", 0)
        meta_parts = [p for p in [first_tag, f"{bitrate} kbps" if bitrate else ""] if p]
        meta_label = _ElidedLabel("  ·  ".join(meta_parts))
        meta_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        p = meta_label.palette()
        p.setColor(
            QPalette.ColorRole.WindowText,
            meta_label.palette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText),
        )
        meta_label.setPalette(p)
        text_layout.addWidget(meta_label)

        layout.addWidget(text, 1)

        if on_delete is not None:
            self._heart_btn = None
            if on_edit is not None:
                edit_btn = QPushButton()
                edit_btn.setFlat(True)
                edit_btn.setFixedSize(24, 24)
                edit_icon = QIcon.fromTheme("document-edit")
                if edit_icon.isNull():
                    edit_btn.setText("✎")
                else:
                    edit_btn.setIcon(edit_icon)
                edit_btn.clicked.connect(lambda: on_edit(uuid))
                layout.addWidget(edit_btn)
            del_btn = QPushButton()
            del_btn.setFlat(True)
            del_btn.setFixedSize(24, 24)
            icon = QIcon.fromTheme("edit-delete")
            if icon.isNull():
                del_btn.setText("✕")
            else:
                del_btn.setIcon(icon)
            del_btn.clicked.connect(lambda: on_delete(uuid))
            layout.addWidget(del_btn)
        else:
            self._heart_btn = QPushButton()
            self._heart_btn.setFlat(True)
            self._heart_btn.setFixedSize(24, 24)
            self._heart_btn.setCheckable(True)
            is_fav = favourites.is_favourite(uuid)
            self._heart_btn.setChecked(is_fav)
            self._update_heart(is_fav)
            self._heart_btn.toggled.connect(lambda checked, u=uuid: self._on_heart(u, checked))
            layout.addWidget(self._heart_btn)

    def set_favicon(self, data: bytes):
        pix = QPixmap()
        pix.loadFromData(data)
        if not pix.isNull():
            self._favicon.setPixmap(
                pix.scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )

    def set_playing(self, playing: bool):
        self.setAutoFillBackground(True)
        p = self.palette()
        if playing:
            highlight = QPalette().color(QPalette.ColorRole.Highlight)
            highlight.setAlpha(40)
            p.setColor(QPalette.ColorRole.Window, highlight)
            self._favicon.hide()
            self._wave.start()
        else:
            p.setColor(QPalette.ColorRole.Window, QPalette().color(QPalette.ColorRole.Base))
            self._wave.stop()
            self._favicon.show()
        self.setPalette(p)

    def update_favourite(self, is_fav: bool):
        if self._heart_btn is None:
            return
        self._heart_btn.blockSignals(True)
        self._heart_btn.setChecked(is_fav)
        self._heart_btn.blockSignals(False)
        self._update_heart(is_fav)

    def _update_heart(self, is_fav: bool):
        if self._heart_btn is None:
            return
        icon = QIcon.fromTheme("emblem-favorite" if is_fav else "emblem-favorite-symbolic")
        if icon.isNull():
            self._heart_btn.setText("♥" if is_fav else "♡")
            self._heart_btn.setIcon(QIcon())
        else:
            self._heart_btn.setText("")
            self._heart_btn.setIcon(icon)

    def _on_heart(self, uuid: str, checked: bool):
        self._update_heart(checked)
        self.favourite_toggled.emit(uuid, checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.play_requested.emit(self._station)
        super().mousePressEvent(event)


class StationListWidget(QWidget):
    station_play_requested = pyqtSignal(dict)
    favourite_toggled = pyqtSignal(str, bool)
    search_requested = pyqtSignal(str)
    station_delete_requested = pyqtSignal(str)
    station_edit_requested = pyqtSignal(str)

    def __init__(self, favourites: FavouritesManager, parent=None):
        super().__init__(parent)
        self._favourites = favourites
        self._current_view = "all"
        self._fav_uuids: set[str] = set()
        self._recent_uuids: list[str] = []
        self._row_widgets: dict[str, StationRowWidget] = {}
        self._playing_uuid: str | None = None
        self._pool = QThreadPool.globalInstance()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        search_bar = QWidget()
        search_layout = QHBoxLayout(search_bar)
        search_layout.setContentsMargins(8, 4, 8, 4)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search stations…")
        self._search_input.setClearButtonEnabled(True)
        search_layout.addWidget(self._search_input)

        layout.addWidget(search_bar)

        self._list = QListWidget()
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list.setSpacing(0)
        layout.addWidget(self._list)

        self._error_label = QLabel()
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._error_label.setWordWrap(True)
        self._error_label.hide()
        layout.addWidget(self._error_label)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._on_search_debounced)
        self._search_input.textChanged.connect(lambda: self._search_timer.start(350))

    def set_stations(self, stations: list[dict], deletable: bool = False):
        self._error_label.hide()
        self._list.show()
        self._list.clear()
        self._row_widgets.clear()

        for station in stations:
            uuid = station.get("stationuuid", "")
            item = QListWidgetItem(self._list)
            item.setSizeHint(QSize(0, 56))
            item.setData(Qt.ItemDataRole.UserRole, station)

            on_delete = (lambda u: self.station_delete_requested.emit(u)) if deletable else None
            on_edit = (lambda u: self.station_edit_requested.emit(u)) if deletable else None
            row = StationRowWidget(station, self._favourites, on_delete=on_delete, on_edit=on_edit)
            self._list.setItemWidget(item, row)
            self._row_widgets[uuid] = row

            row.play_requested.connect(
                lambda s=station, i=item: self._on_row_play(s, i)
            )
            if not deletable:
                row.favourite_toggled.connect(self.favourite_toggled)

            favicon_url = station.get("favicon", "")
            if favicon_url:
                loader = _FaviconLoader(uuid, favicon_url)
                loader.signals.loaded.connect(self._on_favicon_loaded)
                self._pool.start(loader)

        if self._playing_uuid and self._playing_uuid in self._row_widgets:
            self._row_widgets[self._playing_uuid].set_playing(True)

        self._apply_filter()

    def set_error(self, message: str):
        self._list.hide()
        self._error_label.setText(message)
        self._error_label.show()

    def set_view(self, view: str, fav_uuids: set[str], recent_uuids: list[str]):
        self._current_view = view
        self._fav_uuids = fav_uuids
        self._recent_uuids = recent_uuids
        self._apply_filter()

    def mark_playing(self, uuid: str):
        if self._playing_uuid and self._playing_uuid in self._row_widgets:
            self._row_widgets[self._playing_uuid].set_playing(False)
        self._playing_uuid = uuid
        if uuid in self._row_widgets:
            self._row_widgets[uuid].set_playing(True)

    def update_favourite(self, uuid: str, is_fav: bool):
        if uuid in self._row_widgets:
            self._row_widgets[uuid].update_favourite(is_fav)
        if self._current_view == "favourites":
            self._apply_filter()

    def _on_row_play(self, station: dict, item: QListWidgetItem):
        self._list.setCurrentItem(item)
        self.station_play_requested.emit(station)

    def _on_favicon_loaded(self, uuid: str, data: bytes):
        if uuid in self._row_widgets:
            self._row_widgets[uuid].set_favicon(data)

    def _on_search_debounced(self):
        text = self._search_input.text().strip()
        self._apply_filter()
        if len(text) >= 2:
            self.search_requested.emit(text)

    def _apply_filter(self):
        words = self._search_input.text().lower().split()
        recent_set = set(self._recent_uuids)

        for i in range(self._list.count()):
            item = self._list.item(i)
            station = item.data(Qt.ItemDataRole.UserRole)
            if not station:
                continue
            uuid = station.get("stationuuid", "")

            visible = True
            if self._current_view == "favourites":
                visible = uuid in self._fav_uuids
            elif self._current_view == "recent":
                visible = uuid in recent_set

            if words:
                combined = (
                    station.get("name", "") + " " +
                    station.get("tags", "") + " " +
                    station.get("country", "") + " " +
                    station.get("language", "")
                ).lower()
                if not all(w in combined for w in words):
                    visible = False

            item.setHidden(not visible)
