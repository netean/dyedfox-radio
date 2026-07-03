from collections import deque

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

try:
    import dbus
    from gi.repository import GLib
    _DBUS_OK = True
except Exception:
    _DBUS_OK = False

_SERVICE = "org.freedesktop.Notifications"
_PATH = "/org/freedesktop/Notifications"


class DBusNotifier(QObject):
    """Desktop notifications via the freedesktop D-Bus API.

    Sending over D-Bus (instead of notify-send) lets each notification carry a
    'default' action, so clicking its body raises the app window — the `clicked`
    signal fires for that.

    Every song posts a fresh notification (no replaces_id): KDE does not emit
    NotificationClosed when a bubble expires into the history, so any attempt to
    replace-in-place ends up silently updating a history entry that never pops.

    Degrades gracefully: if python-dbus, the notification service, or the
    'actions' capability is unavailable, `available` is False and callers fall
    back to notify-send / the tray bubble.
    """

    clicked = pyqtSignal()  # the notification body (default action) was activated

    def __init__(self, app_name: str = "Dyedfox Radio", parent=None):
        super().__init__(parent)
        self._app_name = app_name
        self._iface = None
        # Ids we sent, so we only react to clicks on our own notifications (not
        # other apps'). Bounded, since KDE never tells us when they close.
        self._our_ids: deque[int] = deque(maxlen=64)
        self._supports_actions = False
        if _DBUS_OK:
            self._setup()

    @property
    def available(self) -> bool:
        return self._iface is not None

    def _setup(self):
        try:
            bus = dbus.SessionBus()
            proxy = bus.get_object(_SERVICE, _PATH)
            iface = dbus.Interface(proxy, _SERVICE)
            # Probe the service is actually present; also tells us if it supports
            # actions (needed for click-to-raise). A missing daemon raises here.
            caps = [str(c) for c in iface.GetCapabilities()]
            self._supports_actions = "actions" in caps
            self._iface = iface
            bus.add_signal_receiver(
                self._on_action, signal_name="ActionInvoked",
                dbus_interface=_SERVICE, path=_PATH,
            )
            # Dispatch incoming D-Bus signals from Qt's event loop, mirroring the
            # MPRIS poller. Iterating the shared default context is idempotent, so
            # running alongside that poller is harmless.
            context = GLib.MainContext.default()
            self._poller = QTimer(self)
            self._poller.timeout.connect(
                lambda: context.iteration(False) if context.pending() else None
            )
            self._poller.start(50)
        except Exception as e:
            print(f"dyedfox-radio: notifications D-Bus unavailable: {e}", flush=True)
            self._iface = None

    def notify(self, summary: str, body: str, icon: str = "", timeout_ms: int = 3000) -> bool:
        """Show a fresh notification. Returns True if sent over D-Bus."""
        if self._iface is None:
            return False
        app_icon = icon if icon else "dyedfox-radio"
        actions = dbus.Array(
            ["default", ""] if self._supports_actions else [], signature="s"
        )
        hints = dbus.Dictionary(
            {"desktop-entry": dbus.String("dyedfox-radio")}, signature="sv"
        )
        try:
            nid = int(self._iface.Notify(
                self._app_name,
                dbus.UInt32(0),  # 0 = always a new bubble, never replace in place
                app_icon,
                summary,
                body,
                actions,
                hints,
                dbus.Int32(timeout_ms),
            ))
            self._our_ids.append(nid)
            return True
        except Exception as e:
            print(f"dyedfox-radio: Notify failed: {e}", flush=True)
            return False

    def _on_action(self, nid, action_key):
        if int(nid) in self._our_ids and str(action_key) == "default":
            self.clicked.emit()
