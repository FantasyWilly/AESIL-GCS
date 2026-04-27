

try:
    from PyQt6.QtWidgets import (
        QCheckBox,
        QFormLayout,
        QGridLayout,
        QGroupBox,
        QLabel,
        QLineEdit,
        QPlainTextEdit,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover
    from PySide6.QtWidgets import (
        QCheckBox,
        QFormLayout,
        QGridLayout,
        QGroupBox,
        QLabel,
        QLineEdit,
        QPlainTextEdit,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )


class ControlPanel(QWidget):
    def __init__(self, rosbridge_url: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.url_input = QLineEdit(rosbridge_url)
        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        self.export_csv_button = QPushButton("Export CSV")
        self.export_xlsx_button = QPushButton("Export XLSX")
        self.save_image_button = QPushButton("Save Trajectory PNG")
        self.clear_overlay_button = QPushButton("Clear Overlay")
        self.select_mbtiles_button = QPushButton("Select MBTiles")
        self.split_view_checkbox = QCheckBox("Map/Video split")
        self.status_label = QLabel("Idle")
        self.aircraft_label = QLabel("--")
        self.target_label = QLabel("0")
        self.offline_map_label = QLabel("No offline map loaded")
        self.test_mode_checkbox = QCheckBox("Enable test mode")
        self.topic_external_label = QLabel("Offline")
        self.topic_mavros_label = QLabel("Offline")
        self.red_lat_input = QLineEdit()
        self.red_lon_input = QLineEdit()
        self.blue_lat_input = QLineEdit()
        self.blue_lon_input = QLineEdit()
        self.red_error_label = QLabel("--")
        self.blue_error_label = QLabel("--")
        self.debug_checkbox = QCheckBox("Enable debug")
        self.debug_output = QPlainTextEdit()
        self.debug_output.setReadOnly(True)
        self.debug_output.setMaximumBlockCount(300)
        self.disconnect_button.setEnabled(False)
        self.status_label.setWordWrap(True)
        self.offline_map_label.setWordWrap(True)
        self.red_error_label.setWordWrap(True)
        self.blue_error_label.setWordWrap(True)
        self.topic_external_label.setWordWrap(True)
        self.topic_mavros_label.setWordWrap(True)

        # 設定預設值
        self.red_lat_input.setText("23.7021050")
        self.red_lon_input.setText("120.4231000")
        self.blue_lat_input.setText("23.7021560")
        self.blue_lon_input.setText("120.4231657")

        form = QFormLayout()
        form.addRow("ROSBridge URL", self.url_input)
        form.addRow("Offline Map", self.offline_map_label)
        form.addRow("Aircraft", self.aircraft_label)
        form.addRow("Targets", self.target_label)

        topic_group = QGroupBox("Topics")
        topic_form = QFormLayout(topic_group)
        topic_form.addRow("Topic1 /external/target_position", self.topic_external_label)
        topic_form.addRow("Topic2 /mavros/global_position/raw/fix", self.topic_mavros_label)

        test_group = QGroupBox("Test Mode")
        test_layout = QVBoxLayout(test_group)
        test_layout.addWidget(self.test_mode_checkbox)

        preset_form = QGridLayout()
        preset_form.addWidget(QLabel("Red lat"), 0, 0)
        preset_form.addWidget(self.red_lat_input, 0, 1)
        preset_form.addWidget(QLabel("Red lon"), 0, 2)
        preset_form.addWidget(self.red_lon_input, 0, 3)
        preset_form.addWidget(QLabel("Blue lat"), 1, 0)
        preset_form.addWidget(self.blue_lat_input, 1, 1)
        preset_form.addWidget(QLabel("Blue lon"), 1, 2)
        preset_form.addWidget(self.blue_lon_input, 1, 3)
        test_layout.addLayout(preset_form)

        error_form = QFormLayout()
        error_form.addRow("Red error", self.red_error_label)
        error_form.addRow("Blue error", self.blue_error_label)
        test_layout.addLayout(error_form)

        debug_group = QGroupBox("Debug")
        debug_layout = QVBoxLayout(debug_group)
        debug_layout.addWidget(self.debug_checkbox)
        debug_layout.addWidget(self.debug_output)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(topic_group)
        layout.addWidget(test_group)
        layout.addWidget(debug_group)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.disconnect_button)
        layout.addWidget(self.export_csv_button)
        layout.addWidget(self.export_xlsx_button)
        layout.addWidget(self.save_image_button)
        layout.addWidget(self.clear_overlay_button)
        layout.addWidget(self.select_mbtiles_button)
        layout.addStretch(1)
