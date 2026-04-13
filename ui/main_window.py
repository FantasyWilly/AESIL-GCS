

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QWidget

from core.data_manager import DataManager
from core.logger import DataLogger
from core.rosbridge_client import RosbridgeClient
from core.state import AppState
from core.tile_server import TileServer
from ui.map_view import MapView
from ui.widgets import ControlPanel


class StatusBus(QObject):
    status_changed = pyqtSignal(str)


class MainWindow(QMainWindow):
    def __init__(self, rosbridge_url: str) -> None:
        super().__init__()
        self.setWindowTitle("AESIL GCS")
        self.resize(1180, 700)

        self.state = AppState()
        self.logger = DataLogger()
        self.data_manager = DataManager(self.state, self.logger)
        self.tile_server = TileServer()
        self.tile_server.start()
        self.status_bus = StatusBus()
        self.status_bus.status_changed.connect(self._apply_status)
        self.client = RosbridgeClient(
            url=rosbridge_url,
            topics=[
                DataManager.AIRCRAFT_TOPIC,
                DataManager.TARGET_TOPIC,
            ],
            on_message=self.data_manager.handle_message,
            on_status=self.update_status,
        )

        self.map_view = MapView(self.state)
        self.panel = ControlPanel(rosbridge_url)
        self.map_view.set_offline_tile_template(self.tile_server.offline_tile_template)
        self._load_default_mbtiles()
        self._wire_signals()

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.addWidget(self.map_view, stretch=4)
        layout.addWidget(self.panel, stretch=1)
        self.setCentralWidget(root)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_view)
        self.refresh_timer.start(500)

    def _wire_signals(self) -> None:
        self.panel.connect_button.clicked.connect(self.connect_rosbridge)
        self.panel.disconnect_button.clicked.connect(self.disconnect_rosbridge)
        self.panel.export_csv_button.clicked.connect(self.export_csv)
        self.panel.export_xlsx_button.clicked.connect(self.export_xlsx)
        self.panel.save_image_button.clicked.connect(self.save_image)
        self.panel.select_mbtiles_button.clicked.connect(self.select_mbtiles)

    def _load_default_mbtiles(self) -> None:
        default_mbtiles = Path.cwd() / "data" / "offline.mbtiles"
        if not default_mbtiles.exists():
            return
        try:
            self.tile_server.set_mbtiles(default_mbtiles)
        except Exception:
            return
        self.panel.offline_map_label.setText(default_mbtiles.name)
        self.map_view.set_offline_map_info(self.tile_server.get_source_info())

    def select_mbtiles(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select MBTiles",
            str(Path.cwd()),
            "MBTiles Files (*.mbtiles)",
        )
        if not file_path:
            return
        try:
            self.tile_server.set_mbtiles(file_path)
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "MBTiles Error", str(exc))
            return

        source = self.tile_server.get_source_info()
        self.panel.offline_map_label.setText(Path(source["path"]).name)
        self.map_view.set_offline_tile_template(self.tile_server.offline_tile_template)
        self.map_view.set_offline_map_info(source)
        self.map_view.reload_offline_map()
        self.map_view.reset_view_to_offline_bounds()
        self.update_status(f"Loaded MBTiles: {source['name']}")

    def connect_rosbridge(self) -> None:
        self.client.url = self.panel.url_input.text().strip()
        try:
            self.client.connect()
        except Exception as exc:  # pragma: no cover
            QMessageBox.critical(self, "ROSBridge Error", str(exc))

    def disconnect_rosbridge(self) -> None:
        self.client.disconnect()

    def update_status(self, status: str) -> None:
        self.status_bus.status_changed.emit(status)

    def _apply_status(self, status: str) -> None:
        self.panel.status_label.setText(status)
        status_lower = status.lower()
        is_connected = "subscribed:" in status_lower or "updated from" in status_lower
        is_connecting = "connecting to" in status_lower
        self.panel.connect_button.setEnabled(not is_connected and not is_connecting)
        self.panel.disconnect_button.setEnabled(is_connected or is_connecting)

    def refresh_view(self) -> None:
        aircraft = self.state.snapshot_aircraft()
        if aircraft:
            point = aircraft.point
            self.panel.aircraft_label.setText(
                f"{point.latitude:.6f}, {point.longitude:.6f}, alt {point.altitude:.1f} m"
            )
        self.panel.target_label.setText(str(len(self.state.snapshot_targets())))
        self.map_view.sync_state()

    def export_csv(self) -> None:
        default_path = self._default_output_path("flight_log.csv")
        file_path, _ = QFileDialog.getSaveFileName(self, "Export CSV", str(default_path), "CSV Files (*.csv)")
        if file_path:
            path = self.logger.export_csv(file_path)
            self.update_status(f"Saved CSV: {path}")

    def export_xlsx(self) -> None:
        default_path = self._default_output_path("flight_log.xlsx")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export XLSX",
            str(default_path),
            "Excel Files (*.xlsx)",
        )
        if file_path:
            path = self.logger.export_xlsx(file_path)
            self.update_status(f"Saved XLSX: {path}")

    def save_image(self) -> None:
        default_path = self._default_output_path("trajectory.png")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Trajectory PNG",
            str(default_path),
            "PNG Files (*.png)",
        )
        if file_path:
            path = self.map_view.save_image(file_path)
            self.update_status(f"Saved image: {path}")

    def _default_output_path(self, filename: str) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path.cwd() / "output"
        return output_dir / f"{stamp}_{filename}"

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.client.disconnect()
        self.tile_server.stop()
        super().closeEvent(event)
