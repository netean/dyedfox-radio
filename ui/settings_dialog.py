from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QCheckBox, QComboBox,
    QDialogButtonBox, QGroupBox, QLabel,
)
from PyQt6.QtCore import QEvent

from data.settings import Settings


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Settings")
        self.setMinimumWidth(380)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Startup ---
        startup = QGroupBox("Startup")
        startup_layout = QVBoxLayout(startup)

        self._start_minimized = QCheckBox("Start minimized to tray")
        self._start_minimized.setChecked(settings["start_minimized"])
        startup_layout.addWidget(self._start_minimized)

        self._autoplay_last = QCheckBox("Autoplay last station")
        self._autoplay_last.setChecked(settings["autoplay_last"])
        startup_layout.addWidget(self._autoplay_last)

        note = QLabel("Startup options take effect on next launch.")
        note.setEnabled(False)
        startup_layout.addWidget(note)

        layout.addWidget(startup)

        # --- Stations ---
        stations = QGroupBox("Stations")
        stations_layout = QFormLayout(stations)
        stations_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)

        self._limit = QComboBox()
        for n in [50, 100, 200]:
            self._limit.addItem(f"{n} stations", n)
        current = settings["station_limit"]
        self._limit.setCurrentIndex({50: 0, 100: 1, 200: 2}.get(current, 1))
        stations_layout.addRow("Top stations to load:", self._limit)

        layout.addWidget(stations)

        # --- Notifications ---
        notif = QGroupBox("Notifications")
        notif_layout = QVBoxLayout(notif)

        self._notifications = QCheckBox("Show song change notifications")
        self._notifications.setChecked(settings["notifications"])
        notif_layout.addWidget(self._notifications)

        layout.addWidget(notif)

        # --- Buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.PaletteChange:
            for w in self.findChildren(QLabel | QGroupBox):
                w.update()
        super().changeEvent(event)

    def _save(self):
        self._settings["start_minimized"] = self._start_minimized.isChecked()
        self._settings["autoplay_last"] = self._autoplay_last.isChecked()
        self._settings["station_limit"] = self._limit.currentData()
        self._settings["notifications"] = self._notifications.isChecked()
        self._settings.save()
        self.accept()
