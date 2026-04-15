

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QTabWidget, QWidget

from core.data_manager import DataManager
from core.logger import DataLogger
from core.rosbridge_client import RosbridgeClient
from core.state import AppState, GeoPoint, TargetRecord
from core.tile_server import TileServer
from ui.map_view import MapView
from ui.camera_panel import CameraControlPanel
from ui.widgets import ControlPanel
from utils.geo import distance_meters


class StatusBus(QObject):
    status_changed = pyqtSignal(str)


class DebugBus(QObject):
    debug_changed = pyqtSignal(str)


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
        self.debug_bus = DebugBus()
        self.debug_bus.debug_changed.connect(self._apply_debug)
        self.client = RosbridgeClient(
            url=rosbridge_url,
            topics=[
                DataManager.AIRCRAFT_TOPIC,
                DataManager.TARGET_TOPIC,
            ],
            on_message=self.data_manager.handle_message,
            on_status=self.update_status,
            on_debug=self.update_debug,
        )

        self.map_view = MapView(self.state)
        self.panel = ControlPanel(rosbridge_url)
        self.map_view.set_offline_tile_template(self.tile_server.offline_tile_template)
        self._load_default_mbtiles()
        self._wire_signals()

        self.right_tabs = QTabWidget()
        self.right_tabs.addTab(self.panel, "GCS")
        self.right_tabs.addTab(CameraControlPanel(), "Camera")

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.addWidget(self.map_view, stretch=4)
        layout.addWidget(self.right_tabs, stretch=1)
        self.setCentralWidget(root)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_view)
        self.refresh_timer.start(500)
        self._topic_last_seen: dict[str, datetime] = {}

    def _wire_signals(self) -> None:
        self.panel.connect_button.clicked.connect(self.connect_rosbridge)
        self.panel.disconnect_button.clicked.connect(self.disconnect_rosbridge)
        self.panel.export_csv_button.clicked.connect(self.export_csv)
        self.panel.export_xlsx_button.clicked.connect(self.export_xlsx)
        self.panel.save_image_button.clicked.connect(self.save_image)
        self.panel.clear_overlay_button.clicked.connect(self.clear_overlay)
        self.panel.select_mbtiles_button.clicked.connect(self.select_mbtiles)
        self.panel.debug_checkbox.toggled.connect(self._toggle_debug)

    def _toggle_debug(self, enabled: bool) -> None:
        self.client.debug_enabled = enabled
        self._apply_debug("Debug enabled" if enabled else "Debug disabled")

    def update_debug(self, message: str) -> None:
        self.debug_bus.debug_changed.emit(message)

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
        status_lower = status.lower()
        if status_lower.startswith("updated from "):
            topic = status[len("Updated from "):].strip()
            if topic:
                self._topic_last_seen[topic] = datetime.utcnow()

    def _apply_debug(self, message: str) -> None:
        self.panel.debug_output.appendPlainText(message)

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
                f"{point.latitude:.6f}, {point.longitude:.6f}"
            )
        else:
            self.panel.aircraft_label.setText("--")
        self.panel.target_label.setText(str(len(self.state.snapshot_targets())))
        self._refresh_test_mode()
        self._update_topic_status()
        self.map_view.sync_state()

    def _update_topic_status(self) -> None:
        now = datetime.utcnow()
        self._apply_topic_status(self.panel.topic_external_label, DataManager.TARGET_TOPIC, now)
        self._apply_topic_status(self.panel.topic_mavros_label, DataManager.AIRCRAFT_TOPIC, now)

    def _apply_topic_status(self, label, topic: str, now: datetime) -> None:
        last_seen = self._topic_last_seen.get(topic)
        if last_seen and (now - last_seen).total_seconds() <= 2.0:
            label.setText("Online")
            label.setStyleSheet("color: #16a34a; font-weight: 600;")
        else:
            label.setText("Offline")
            label.setStyleSheet("color: #9ca3af; font-weight: 600;")

    def _refresh_test_mode(self) -> None:
        test_enabled = self.panel.test_mode_checkbox.isChecked()
        reference_targets = self._build_reference_targets() if test_enabled else []
        self.map_view.set_test_mode_payload(
            {
                "enabled": test_enabled,
                "referenceTargets": reference_targets,
            }
        )
        self._update_test_errors(test_enabled)

    def _build_reference_targets(self) -> list[dict[str, object]]:
        references: list[dict[str, object]] = []
        red_point = self._parse_reference_point(self.panel.red_lat_input.text(), self.panel.red_lon_input.text(), "red")
        blue_point = self._parse_reference_point(
            self.panel.blue_lat_input.text(), self.panel.blue_lon_input.text(), "blue"
        )
        if red_point:
            references.append(
                {
                    "key": "red",
                    "label": "Red preset",
                    "color": "red",
                    "position": self._point_to_dict(red_point),
                }
            )
        if blue_point:
            references.append(
                {
                    "key": "blue",
                    "label": "Blue preset",
                    "color": "blue",
                    "position": self._point_to_dict(blue_point),
                }
            )
        return references

    def _update_test_errors(self, test_enabled: bool) -> None:
        if not test_enabled:
            self.panel.red_error_label.setText("--")
            self.panel.blue_error_label.setText("--")
            return

        targets = self.state.snapshot_targets()
        red_reference = self._parse_reference_point(
            self.panel.red_lat_input.text(), self.panel.red_lon_input.text(), "red"
        )
        blue_reference = self._parse_reference_point(
            self.panel.blue_lat_input.text(), self.panel.blue_lon_input.text(), "blue"
        )

        self.panel.red_error_label.setText(self._format_target_error("red", red_reference, targets))
        self.panel.blue_error_label.setText(self._format_target_error("blue", blue_reference, targets))

    def _format_target_error(
        self,
        color: str,
        reference: GeoPoint | None,
        targets: dict[str, TargetRecord],
    ) -> str:
        if reference is None:
            return "Preset not set"

        matches = self._find_color_targets(targets, color)
        if not matches:
            return "No detected target"

        avg_lat, avg_lon = self._average_position(matches)
        avg_point = GeoPoint(latitude=avg_lat, longitude=avg_lon)
        delta_m = distance_meters(reference, avg_point)
        return (
            f"{delta_m:.2f} m\n"
            f"avg: {avg_lat:.6f}, {avg_lon:.6f} ({len(matches)} pts)"
        )

    def _find_color_targets(self, targets: dict[str, TargetRecord], color: str) -> list[TargetRecord]:
        results: list[TargetRecord] = []
        for target in targets.values():
            label_lower = target.label.lower()
            vehicle_lower = target.vehicle_name.lower()
            if color in label_lower or color in vehicle_lower:
                results.append(target)
        return results

    def _average_position(self, targets: list[TargetRecord]) -> tuple[float, float]:
        lat_sum = 0.0
        lon_sum = 0.0
        for target in targets:
            lat_sum += target.position.latitude
            lon_sum += target.position.longitude
        count = max(len(targets), 1)
        return lat_sum / count, lon_sum / count

    def _parse_reference_point(self, lat_text: str, lon_text: str, source: str) -> GeoPoint | None:
        try:
            latitude = float(lat_text.strip())
            longitude = float(lon_text.strip())
        except ValueError:
            return None
        return GeoPoint(latitude=latitude, longitude=longitude, source=source)

    def _point_to_dict(self, point: GeoPoint) -> dict[str, float]:
        return {
            "latitude": point.latitude,
            "longitude": point.longitude,
            "altitude": point.altitude,
        }

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

    def clear_overlay(self) -> None:
        self.state.clear()
        self.map_view.clear_overlay()
        self.panel.aircraft_label.setText("--")
        self.panel.target_label.setText("0")

    def _default_output_path(self, filename: str) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path.cwd() / "output"
        return output_dir / f"{stamp}_{filename}"

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self.client.disconnect()
        self.tile_server.stop()
        super().closeEvent(event)
