import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class GStreamerBackend(QObject):
    metadata_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = Gst.ElementFactory.make("playbin", "player")
        if self._player is None:
            raise RuntimeError(
                "Failed to create GStreamer playbin element. "
                "Make sure gstreamer and gst-plugins-good are installed."
            )

        # pulsesink (also works via PipeWire's PA layer) follows the default
        # sink dynamically, so Bluetooth headphones picked up mid-session work
        # without restarting. autoaudiosink locks to the device at play time.
        audio_sink = Gst.ElementFactory.make("pulsesink", "audio_sink")
        if audio_sink is not None:
            self._player.set_property("audio-sink", audio_sink)

        self._bus = self._player.get_bus()
        self._last_url: str | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_bus)
        self._timer.start(200)

    def play(self, url: str):
        self._player.set_state(Gst.State.NULL)
        self._player.set_property("uri", url)
        self._last_url = url
        self._player.set_state(Gst.State.PLAYING)
        self.playback_started.emit()

    def play_last(self):
        if self._last_url:
            self.play(self._last_url)

    def stop(self):
        self._player.set_state(Gst.State.NULL)
        self.playback_stopped.emit()

    def set_volume(self, value: int):
        self._player.set_property("volume", max(0, min(100, value)) / 100.0)

    def set_muted(self, muted: bool):
        self._player.set_property("mute", muted)

    @property
    def is_muted(self) -> bool:
        return bool(self._player.get_property("mute"))

    @property
    def is_playing(self) -> bool:
        _, state, _ = self._player.get_state(0)
        return state == Gst.State.PLAYING

    @property
    def last_url(self) -> str | None:
        return self._last_url

    def _poll_bus(self):
        while True:
            msg = self._bus.pop()
            if msg is None:
                break
            if msg.type == Gst.MessageType.ERROR:
                err, _ = msg.parse_error()
                self.stop()
                self.error_occurred.emit(str(err))
            elif msg.type == Gst.MessageType.TAG:
                tags = msg.parse_tag()
                ok, title = tags.get_string(Gst.TAG_TITLE)
                if ok and title:
                    self.metadata_changed.emit(title)
