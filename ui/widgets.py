

try:
    from PyQt6.QtWidgets import QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget
except ImportError:  # pragma: no cover
    from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


class ControlPanel(QWidget):
    def __init__(self, rosbridge_url: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.url_input = QLineEdit(rosbridge_url)
        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        self.export_csv_button = QPushButton("Export CSV")
        self.export_xlsx_button = QPushButton("Export XLSX")
        self.save_image_button = QPushButton("Save Trajectory PNG")
        self.select_mbtiles_button = QPushButton("Select MBTiles")
        self.status_label = QLabel("Idle")
        self.aircraft_label = QLabel("--")
        self.target_label = QLabel("0")
        self.offline_map_label = QLabel("No offline map loaded")
        self.disconnect_button.setEnabled(False)
        self.status_label.setWordWrap(True)
        self.offline_map_label.setWordWrap(True)

        form = QFormLayout()
        form.addRow("ROSBridge URL", self.url_input)
        form.addRow("Offline Map", self.offline_map_label)
        form.addRow("Status", self.status_label)
        form.addRow("Aircraft", self.aircraft_label)
        form.addRow("Targets", self.target_label)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.disconnect_button)
        layout.addWidget(self.export_csv_button)
        layout.addWidget(self.export_xlsx_button)
        layout.addWidget(self.save_image_button)
        layout.addWidget(self.select_mbtiles_button)
        layout.addStretch(1)
