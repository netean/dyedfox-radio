from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QFrame, QSystemTrayIcon, QApplication,
)
from pathlib import Path
from PyQt6.QtCore import Qt, QSize, QEvent
from PyQt6.QtGui import QIcon, QShortcut, QKeySequence

from ui.station_list import StationListWidget
from ui.info_panel import InfoPanel
from ui.now_playing import NowPlayingBar
from ui.controls import ControlBar
from ui.settings_dialog import SettingsDialog
from ui.about_dialog import AboutDialog
from ui.add_station_dialog import AddStationDialog
from player.backend import GStreamerBackend
from api.radio_browser import RadioBrowserClient
from data.favourites import FavouritesManager, RecentManager
from data.settings import Settings
from data.custom_stations import CustomStationsManager


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
        self._custom = CustomStationsManager()
        self._current_station: dict | None = None
        self._current_view = "all"
        self._top_stations: list = []
        self._search_results: list = []
        self._last_search_key: tuple = ("", "", "")
        self._last_title: str = ""
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

    def _sep(self, vertical=False) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine if vertical else QFrame.Shape.HLine)
        return sep

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

        content_layout.addWidget(self._sep(vertical=True))

        self._station_list = StationListWidget(self._favourites, self._settings)
        content_layout.addWidget(self._station_list, 1)

        content_layout.addWidget(self._sep(vertical=True))

        self._info_panel = InfoPanel()
        content_layout.addWidget(self._info_panel)

        root_layout.addWidget(self._sep())

        self._now_playing = NowPlayingBar()
        root_layout.addWidget(self._now_playing)

        root_layout.addWidget(self._sep())

        self._controls = ControlBar()
        root_layout.addWidget(self._controls)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(148)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(2)

        _sub_style = "QPushButton { text-align: left; padding: 2px 8px 2px 20px; font-size: small; }"
        _nav_style = "QPushButton { text-align: left; padding: 4px 8px; }"
        self._nav_btns: dict[str, QPushButton] = {}

        for label, view, icon_name in [
            (self.tr("All stations"), "all",        "network-wireless"),
            (self.tr("Favourites"),   "favourites", "emblem-favorite"),
        ]:
            btn = QPushButton(label)
            btn.setFlat(True)
            btn.setCheckable(True)
            btn.setIcon(QIcon.fromTheme(icon_name))
            btn.setIconSize(QSize(16, 16))
            btn.setStyleSheet(_nav_style)
            btn.clicked.connect(lambda _, v=view: self._switch_view(v))
            layout.addWidget(btn)
            self._nav_btns[view] = btn

        custom_btn = QPushButton(self.tr("Custom"))
        custom_btn.setFlat(True)
        custom_btn.setCheckable(True)
        custom_btn.setIcon(QIcon.fromTheme("document-edit"))
        custom_btn.setIconSize(QSize(16, 16))
        custom_btn.setStyleSheet(_nav_style)
        custom_btn.clicked.connect(lambda: self._switch_view("custom"))
        layout.addWidget(custom_btn)
        self._nav_btns["custom"] = custom_btn

        self._add_station_btn = QPushButton(self.tr("+ Add station"))
        self._add_station_btn.setFlat(True)
        self._add_station_btn.setStyleSheet(_sub_style)
        self._add_station_btn.clicked.connect(self._on_add_custom_station)
        self._add_station_btn.hide()
        layout.addWidget(self._add_station_btn)

        recent_btn = QPushButton(self.tr("Recent"))
        recent_btn.setFlat(True)
        recent_btn.setCheckable(True)
        recent_btn.setIcon(QIcon.fromTheme("document-open-recent"))
        recent_btn.setIconSize(QSize(16, 16))
        recent_btn.setStyleSheet(_nav_style)
        recent_btn.clicked.connect(lambda: self._switch_view("recent"))
        layout.addWidget(recent_btn)
        self._nav_btns["recent"] = recent_btn

        self._clear_recent_btn = QPushButton(self.tr("Clear recent"))
        self._clear_recent_btn.setFlat(True)
        self._clear_recent_btn.setStyleSheet(_sub_style)
        self._clear_recent_btn.clicked.connect(self._on_clear_recent)
        self._clear_recent_btn.hide()
        layout.addWidget(self._clear_recent_btn)

        self._nav_btns["all"].setChecked(True)

        layout.addStretch()

        layout.addWidget(self._sep())

        self._settings_btn = QPushButton(self.tr("Settings"))
        self._settings_btn.setFlat(True)
        self._settings_btn.setIcon(QIcon.fromTheme("preferences-system"))
        self._settings_btn.setIconSize(QSize(16, 16))
        self._settings_btn.setStyleSheet("QPushButton { text-align: left; padding: 4px 8px; }")
        self._settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self._settings_btn)

        self._about_btn = QPushButton(self.tr("About"))
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
        self._station_list.search_params_changed.connect(self._on_search_params_changed)
        self._station_list.station_delete_requested.connect(self._on_custom_delete)
        self._station_list.station_edit_requested.connect(self._on_custom_edit)

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
            if self._current_view == "all":
                self._station_list.set_stations(stations)
            if autoplay_uuid:
                match = next((s for s in stations if s.get("stationuuid") == autoplay_uuid), None)
                if match:
                    self._on_station_play(match)
                elif autoplay_uuid.startswith("custom-"):
                    custom_match = next((s for s in self._custom.all() if s.get("stationuuid") == autoplay_uuid), None)
                    if custom_match:
                        self._on_station_play(custom_match)
                else:
                    self._api.stations_by_uuids(
                        [autoplay_uuid],
                        on_result=lambda result: self._on_station_play(result[0]) if result else None,
                    )

        self._api.top_stations(
            limit=self._settings["station_limit"],
            on_result=on_loaded,
            on_error=lambda e: self._station_list.set_error(
                self.tr("Could not load stations — check your connection"),
                on_retry=lambda: self.load_top_stations(),
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
        self._settings["last_view"] = view
        self._settings.save()
        self._search_results = []
        self._last_search_key = ("", "", "")
        for v, btn in self._nav_btns.items():
            btn.setChecked(v == view)
        self._clear_recent_btn.setVisible(view == "recent")
        self._add_station_btn.setVisible(view == "custom")

        # Set the filter mode first so it's in place when async stations arrive.
        self._station_list.set_view(view, self._favourites.uuids(), self._recent.uuids())

        if view == "custom":
            self._station_list.set_stations(self._custom.all(), deletable=True)
            return

        if view == "favourites":
            uuids = list(self._favourites.uuids())
            self._api.stations_by_uuids(
                uuids,
                on_result=self._station_list.set_stations,
                on_error=lambda e: self._station_list.set_error(
                    self.tr("Could not load favourites — check your connection"),
                    on_retry=lambda: self._switch_view("favourites"),
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
                        self.tr("Could not load recent — check your connection"),
                        on_retry=lambda: self._switch_view("recent"),
                    ),
                )
            else:
                self._station_list.set_stations([])
        else:
            if self._top_stations:
                self._station_list.set_stations(self._top_stations)
            else:
                self.load_top_stations()

    def _on_station_play(self, station: dict):
        url = station.get("url_resolved", "")
        if not url:
            return
        self._current_station = station
        self._last_title = ""
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
                    r = _req.get(self_._url, timeout=5, headers={"User-Agent": "dyedfox-radio/1.0"})
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
        if title == self._last_title:
            return
        self._last_title = title
        if self._settings["notifications"] and self._tray and self._current_station:
            self._tray.showMessage(
                self._current_station.get("name", "Dyedfox Radio"),
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
        print(f"dyedfox-radio: stream error: {msg}", flush=True)
        self._now_playing.set_error()
        self._controls.set_playing(False)
        if self._tray:
            station = self._current_station.get("name", "the station") if self._current_station else "the station"
            self._tray.showMessage(
                "Dyedfox Radio",
                self.tr("Could not connect to {0}. The stream may be down or unavailable.").format(station),
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
        self._station_list.mark_stopped()
        if self._mpris:
            self._mpris.update_playback_status()

    def _on_started(self):
        self._controls.set_playing(True)
        self._station_list.mark_resumed()
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

    def _on_search_params_changed(self, name: str, country: str, tag: str, language: str):
        if not name and not country and not tag and not language:
            if self._top_stations:
                self._station_list.set_stations(self._top_stations)
            else:
                self.load_top_stations()
            return

        key = (name, country, tag, language)
        if key == self._last_search_key and self._search_results:
            self._station_list.set_stations(self._search_results)
            return

        self._last_search_key = key

        def _on_result(stations: list):
            self._search_results = stations
            self._station_list.set_stations(stations)

        self._api.search(
            name=name,
            country=country,
            tag=tag,
            language=language,
            limit=self._settings["station_limit"],
            on_result=_on_result,
            on_error=lambda e: print(f"dyedfox-radio: search error: {e}", flush=True),
        )

    def _on_add_custom_station(self):
        dlg = AddStationDialog(self)
        if dlg.exec():
            name, url, favicon, tags, country, language = dlg.values()
            self._custom.add(name, url, favicon, tags, country, language)
            self._station_list.set_stations(self._custom.all(), deletable=True)

    def _on_custom_edit(self, uuid: str):
        station = next((s for s in self._custom.all() if s.get("stationuuid") == uuid), None)
        if not station:
            return
        dlg = AddStationDialog(
            self,
            name=station.get("name", ""),
            url=station.get("url_resolved", ""),
            favicon=station.get("favicon", ""),
            tags=station.get("tags", ""),
            country=station.get("country", ""),
            language=station.get("language", ""),
        )
        if dlg.exec():
            name, url, favicon, tags, country, language = dlg.values()
            self._custom.update(uuid, name, url, favicon, tags, country, language)
            self._station_list.set_stations(self._custom.all(), deletable=True)

    def _on_custom_delete(self, uuid: str):
        self._custom.remove(uuid)
        self._station_list.set_stations(self._custom.all(), deletable=True)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.PaletteChange:
            for btn in [
                *self._nav_btns.values(),
                self._clear_recent_btn, self._add_station_btn,
                self._settings_btn, self._about_btn,
            ]:
                btn.setStyleSheet(btn.styleSheet())
        super().changeEvent(event)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
