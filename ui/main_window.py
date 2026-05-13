from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QFrame, QSystemTrayIcon, QApplication,
)
from pathlib import Path
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QShortcut, QKeySequence

from ui.station_list import StationListWidget
from ui.info_panel import InfoPanel
from ui.now_playing import NowPlayingBar
from ui.controls import ControlBar
from ui.settings_dialog import SettingsDialog
from ui.about_dialog import AboutDialog
from player.backend import GStreamerBackend
from api.radio_browser import RadioBrowserClient
from data.favourites import FavouritesManager, RecentManager
from data.settings import Settings


class MainWindow(QMainWindow):
    def __init__(
        self,
        backend: GStreamerBackend,
        api: RadioBrowserClient,
        favourites: FavouritesManager,
        recent: RecentManager,
        settings: Settings,
    ):
        super().__init__()
        self._backend = backend
        self._api = api
        self._favourites = favourites
        self._recent = recent
        self._settings = settings
        self._current_station: dict | None = None
        self._current_view = "all"
        self._top_stations: list = []
        self._search_results: list = []
        self._last_search_word: str = ""
        self._tray = None
        self._mpris = None

        self.setWindowTitle("Dyedfox Radio")
        _icon = Path(__file__).parent.parent / "assets" / "icons" / "dyedfox-radio.png"
        self.setWindowIcon(QIcon(str(_icon)))
        self.resize(960, 620)
        self._setup_ui()
        self._connect_signals()
        self._apply_settings()
        self._setup_shortcuts()

    def _setup_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        root_layout.addWidget(content, 1)

        self._sidebar = self._build_sidebar()
        content_layout.addWidget(self._sidebar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        content_layout.addWidget(sep)

        self._station_list = StationListWidget(self._favourites)
        content_layout.addWidget(self._station_list, 1)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        content_layout.addWidget(sep2)

        self._info_panel = InfoPanel()
        content_layout.addWidget(self._info_panel)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.HLine)
        root_layout.addWidget(sep3)

        self._now_playing = NowPlayingBar()
        root_layout.addWidget(self._now_playing)

        sep4 = QFrame()
        sep4.setFrameShape(QFrame.Shape.HLine)
        root_layout.addWidget(sep4)

        self._controls = ControlBar()
        root_layout.addWidget(self._controls)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(148)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(2)

        self._nav_btns: dict[str, QPushButton] = {}
        for label, view, icon_name in [
            ("All stations", "all",        "network-wireless"),
            ("Favourites",   "favourites", "emblem-favorite"),
            ("Recent",       "recent",     "document-open-recent"),
        ]:
            btn = QPushButton(label)
            btn.setFlat(True)
            btn.setCheckable(True)
            btn.setIcon(QIcon.fromTheme(icon_name))
            btn.setIconSize(QSize(16, 16))
            btn.setStyleSheet("QPushButton { text-align: left; padding: 4px 8px; }")
            btn.clicked.connect(lambda _, v=view: self._switch_view(v))
            layout.addWidget(btn)
            self._nav_btns[view] = btn

        self._clear_recent_btn = QPushButton("Clear recent")
        self._clear_recent_btn.setFlat(True)
        self._clear_recent_btn.setStyleSheet(
            "QPushButton { text-align: left; padding: 2px 8px 2px 20px; font-size: small; }"
        )
        self._clear_recent_btn.clicked.connect(self._on_clear_recent)
        self._clear_recent_btn.hide()
        layout.addWidget(self._clear_recent_btn)

        self._nav_btns["all"].setChecked(True)

        layout.addStretch()

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        self._settings_btn = QPushButton("Settings")
        self._settings_btn.setFlat(True)
        self._settings_btn.setIcon(QIcon.fromTheme("preferences-system"))
        self._settings_btn.setIconSize(QSize(16, 16))
        self._settings_btn.setStyleSheet("QPushButton { text-align: left; padding: 4px 8px; }")
        self._settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self._settings_btn)

        self._about_btn = QPushButton("About")
        self._about_btn.setFlat(True)
        self._about_btn.setIcon(QIcon.fromTheme("help-about"))
        self._about_btn.setIconSize(QSize(16, 16))
        self._about_btn.setStyleSheet("QPushButton { text-align: left; padding: 4px 8px; }")
        self._about_btn.clicked.connect(self._open_about)
        layout.addWidget(self._about_btn)

        return sidebar

    def _connect_signals(self):
        self._backend.metadata_changed.connect(self._on_metadata)
        self._backend.error_occurred.connect(self._on_stream_error)
        self._backend.playback_stopped.connect(self._on_stopped)
        self._backend.playback_started.connect(self._on_started)

        self._station_list.station_play_requested.connect(self._on_station_play)
        self._station_list.favourite_toggled.connect(self._on_favourite_toggled)
        self._station_list.search_requested.connect(self._on_search)

        self._controls.playback_toggled.connect(self._on_playback_toggled)
        self._controls.volume_changed.connect(self._on_volume_changed)

        self._info_panel.favourite_toggled.connect(self._on_favourite_toggled)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(QApplication.quit)
        QShortcut(QKeySequence("Ctrl+W"), self).activated.connect(self.hide)

    def _apply_settings(self):
        vol = self._settings["volume"]
        self._controls.set_volume_slider(vol)
        self._backend.set_volume(vol)

    def load_top_stations(self, autoplay_uuid: str = ""):
        def on_loaded(stations: list):
            self._top_stations = stations
            self._station_list.set_stations(stations)
            if autoplay_uuid:
                match = next((s for s in stations if s.get("stationuuid") == autoplay_uuid), None)
                if match:
                    self._on_station_play(match)

        self._api.top_stations(
            limit=self._settings["station_limit"],
            on_result=on_loaded,
            on_error=lambda e: self._station_list.set_error(
                "Could not load stations — check your connection"
            ),
        )

    def set_tray(self, tray):
        self._tray = tray

    def set_mpris(self, mpris):
        self._mpris = mpris

    def _open_settings(self):
        dlg = SettingsDialog(self._settings, self)
        dlg.exec()

    def _open_about(self):
        AboutDialog(self).exec()

    def _switch_view(self, view: str):
        self._current_view = view
        self._search_results = []
        self._last_search_word = ""
        for v, btn in self._nav_btns.items():
            btn.setChecked(v == view)
        self._clear_recent_btn.setVisible(view == "recent")

        # Set the filter mode first so it's in place when async stations arrive.
        self._station_list.set_view(view, self._favourites.uuids(), self._recent.uuids())

        if view == "favourites":
            uuids = list(self._favourites.uuids())
            self._api.stations_by_uuids(
                uuids,
                on_result=self._station_list.set_stations,
                on_error=lambda e: self._station_list.set_error(
                    "Could not load favourites — check your connection"
                ),
            )
        elif view == "recent":
            uuids = self._recent.uuids()
            if uuids:
                def _on_recent_loaded(stations: list, ordered=uuids):
                    by_uuid = {s.get("stationuuid"): s for s in stations}
                    self._station_list.set_stations(
                        [by_uuid[u] for u in ordered if u in by_uuid]
                    )
                self._api.stations_by_uuids(
                    uuids,
                    on_result=_on_recent_loaded,
                    on_error=lambda e: self._station_list.set_error(
                        "Could not load recent — check your connection"
                    ),
                )
            else:
                self._station_list.set_stations([])
        else:
            self._station_list.set_stations(self._top_stations)

    def _on_station_play(self, station: dict):
        url = station.get("url_resolved", "")
        if not url:
            return
        self._current_station = station
        self._backend.play(url)
        self._now_playing.set_station(station.get("name", ""))
        self._now_playing.clear_song()
        self._info_panel.set_station(station, self._favourites.is_favourite(station.get("stationuuid", "")))
        self._station_list.mark_playing(station.get("stationuuid", ""))
        self._recent.add(station.get("stationuuid", ""))

        favicon_url = station.get("favicon", "")
        if favicon_url:
            self._load_panel_favicon(favicon_url)

    def _load_panel_favicon(self, url: str):
        from PyQt6.QtCore import QRunnable, QThreadPool, QObject, pyqtSignal
        import requests as _req

        class _Sig(QObject):
            done = pyqtSignal(bytes)

        class _Loader(QRunnable):
            def __init__(self_, u):
                super().__init__()
                self_.setAutoDelete(True)
                self_._url = u
                self_.signals = _Sig()

            def run(self_):
                try:
                    r = _req.get(self_._url, timeout=5, headers={"User-Agent": "RadioX/1.0"})
                    if r.ok and r.content:
                        self_.signals.done.emit(r.content)
                except Exception:
                    pass

        loader = _Loader(url)
        loader.signals.done.connect(self._info_panel.set_favicon)
        QThreadPool.globalInstance().start(loader)

    def _on_metadata(self, title: str):
        self._now_playing.set_song(title)
        self._info_panel.set_now_playing(title)
        if self._tray and self._current_station:
            self._tray.update_status(self._current_station.get("name", ""), title)
        if self._settings["notifications"] and self._tray and self._current_station:
            self._tray.showMessage(
                self._current_station.get("name", "RadioX"),
                title,
                QSystemTrayIcon.MessageIcon.NoIcon,
                3000,
            )
        if self._mpris and self._current_station:
            self._mpris.update_metadata(
                title,
                self._current_station.get("name", ""),
                self._current_station.get("favicon", ""),
            )

    def _on_stream_error(self, msg: str):
        print(f"radiox: stream error: {msg}", flush=True)
        self._now_playing.set_error()
        self._controls.set_playing(False)
        if self._tray:
            station = self._current_station.get("name", "the station") if self._current_station else "the station"
            self._tray.showMessage(
                "RadioX",
                f"Could not connect to {station}. The stream may be down or unavailable.",
                QSystemTrayIcon.MessageIcon.Warning,
                4000,
            )

    def _on_playback_toggled(self):
        if self._backend.is_playing:
            self._backend.stop()
        else:
            self._backend.play_last()

    def _on_volume_changed(self, value: int):
        self._backend.set_volume(value)
        self._settings["volume"] = value
        self._settings.save()

    def _on_stopped(self):
        self._controls.set_playing(False)
        if self._mpris:
            self._mpris.update_playback_status()

    def _on_started(self):
        self._controls.set_playing(True)
        if self._mpris:
            self._mpris.update_playback_status()

    def _on_clear_recent(self):
        self._recent.clear()
        self._station_list.set_view("recent", self._favourites.uuids(), self._recent.uuids())

    def _on_favourite_toggled(self, uuid: str, is_fav: bool):
        self._favourites.set(uuid, is_fav)
        self._station_list.update_favourite(uuid, is_fav)
        if self._current_station and self._current_station.get("stationuuid") == uuid:
            self._info_panel.set_favourite(is_fav)

    def _on_search(self, text: str):
        words = text.lower().split()
        if not words:
            return

        def _filter(stations: list) -> list:
            if len(words) == 1:
                return stations
            return [
                s for s in stations
                if all(
                    w in (
                        s.get("name", "") + " " +
                        s.get("tags", "") + " " +
                        s.get("country", "") + " " +
                        s.get("language", "")
                    ).lower()
                    for w in words
                )
            ]

        if words[0] == self._last_search_word and self._search_results:
            self._station_list.set_stations(_filter(self._search_results))
            return

        self._last_search_word = words[0]

        def _on_result(stations: list):
            self._search_results = stations
            self._station_list.set_stations(_filter(stations))

        self._api.search(
            words[0],
            on_result=_on_result,
            on_error=lambda e: print(f"radiox: search error: {e}", flush=True),
        )

    def closeEvent(self, event):
        event.ignore()
        self.hide()
