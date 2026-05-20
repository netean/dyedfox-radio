from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDialogButtonBox, QLabel,
)


class AddStationDialog(QDialog):
    def __init__(self, parent=None, name="", url="", favicon=""):
        super().__init__(parent)
        editing = bool(name or url)
        self.setWindowTitle(self.tr("Edit custom station") if editing else self.tr("Add custom station"))
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name = QLineEdit(name)
        self._name.setPlaceholderText(self.tr("My Radio Station"))
        form.addRow(self.tr("Name:"), self._name)

        self._url = QLineEdit(url)
        self._url.setPlaceholderText("http://stream.example.com/live")
        form.addRow(self.tr("Stream URL:"), self._url)

        self._favicon = QLineEdit(favicon)
        self._favicon.setPlaceholderText("https://example.com/logo.png  (optional)")
        form.addRow(self.tr("Logo URL:"), self._favicon)

        layout.addLayout(form)

        self._error = QLabel()
        self._error.setStyleSheet("color: red;")
        self._error.hide()
        layout.addWidget(self._error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate(self):
        name = self._name.text().strip()
        url = self._url.text().strip()
        if not name:
            self._show_error(self.tr("Name is required."))
            return
        if not url.startswith(("http://", "https://")):
            self._show_error(self.tr("Stream URL must start with http:// or https://"))
            return
        self._error.hide()
        self.accept()

    def _show_error(self, msg: str):
        self._error.setText(msg)
        self._error.show()

    def values(self) -> tuple[str, str, str]:
        return (
            self._name.text().strip(),
            self._url.text().strip(),
            self._favicon.text().strip(),
        )
