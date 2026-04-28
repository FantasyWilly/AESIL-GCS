

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QSplitter, QTabWidget, QToolButton, QWidget

from core.data_manager import DataManager
from core.logger import DataLogger
from core.rosbridge_client import RosbridgeClient
from core.state import AppState, GeoPoint, TargetRecord
from core.tile_server import TileServer
from ui.map_view import MapView
from ui.camera_panel import CameraControlPanel
from ui.gazebo_panel import GazeboPanel
from ui.video_stream import VideoStreamWidget
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
        self.video_view = VideoStreamWidget()
        self.panel = ControlPanel(rosbridge_url)
        self.camera_panel = CameraControlPanel()
        self.gazebo_panel = GazeboPanel()
        self.split_overlay_button = QToolButton(self.map_view)
        self.split_overlay_button.setText("Split View")
        self.split_overlay_button.setCheckable(True)
        self.split_overlay_button.setChecked(self.panel.split_view_checkbox.isChecked())
        self.split_overlay_button.setStyleSheet(
            "QToolButton {"
            " background-color: rgba(15, 23, 42, 0.86);"
            " color: #e2e8f0;"
            " border: 1px solid rgba(148, 163, 184, 0.45);"
            " border-radius: 8px;"
            " padding: 6px 10px;"
            "}"
            "QToolButton:checked {"
            " background-color: rgba(30, 64, 175, 0.9);"
            " border-color: rgba(96, 165, 250, 0.9);"
            "}"
        )
        self.map_view.installEventFilter(self)
        self._position_split_overlay_button()
        self.split_overlay_button.show()
        self.map_view.set_offline_tile_template(self.tile_server.offline_tile_template)
        self._load_default_mbtiles()
        self._wire_signals()

        self.right_tabs = QTabWidget()
        self.right_tabs.addTab(self.panel, "GCS")
        self.right_tabs.addTab(self.camera_panel, "Camera")
        self.right_tabs.addTab(self.gazebo_panel, "Gazebo")

        self.left_splitter = QSplitter(Qt.Orientation.Vertical)
        self.left_splitter.addWidget(self.map_view)
        self.left_splitter.addWidget(self.video_view)
        self.video_view.hide()
        self.left_splitter.setSizes([1000, 0])

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.addWidget(self.left_splitter, stretch=4)
        layout.addWidget(self.right_tabs, stretch=1)
        self.setCentralWidget(root)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_view)
        self.refresh_timer.start(500)
        self._topic_last_seen: dict[str, datetime] = {}
        self._latest_bbox_payload: dict | None = None

    def _wire_signals(self) -> None:
        self.panel.connect_button.clicked.connect(self.connect_rosbridge)
        self.panel.disconnect_button.clicked.connect(self.disconnect_rosbridge)
        self.panel.export_csv_button.clicked.connect(self.export_csv)
        self.panel.export_xlsx_button.clicked.connect(self.export_xlsx)
        self.panel.save_image_button.clicked.connect(self.save_image)
        self.panel.clear_overlay_button.clicked.connect(self.clear_overlay)
        self.panel.select_mbtiles_button.clicked.connect(self.select_mbtiles)
        self.panel.debug_checkbox.toggled.connect(self._toggle_debug)
        self.panel.split_view_checkbox.toggled.connect(self._on_panel_split_toggled)
        self.split_overlay_button.toggled.connect(self._on_overlay_split_toggled)
        self.camera_panel.rtsp_apply_requested.connect(self._apply_rtsp_stream)
        self.camera_panel.draw_enabled_changed.connect(self._on_camera_draw_toggled)
        self.camera_panel.clear_bbox_requested.connect(self.video_view.clear_drawn_bbox)
        self.camera_panel.start_tracking_requested.connect(self._call_start_tracking_latest)
        self.camera_panel.start_follow_requested.connect(self._call_start_follow)
        self.camera_panel.stop_follow_requested.connect(self._call_stop_follow)
        self.camera_panel.start_attack_requested.connect(self._call_start_attack)
        self.camera_panel.stop_attack_requested.connect(self._call_stop_attack)
        self.camera_panel.stop_tracking_requested.connect(self._call_stop_tracking)
        self.gazebo_panel.gazebo_apply_requested.connect(self._apply_gazebo_stream)
        self.gazebo_panel.gazebo_rtsp_apply_requested.connect(self._apply_gazebo_rtsp_stream)
        self.gazebo_panel.draw_enabled_changed.connect(self.video_view.set_draw_enabled)
        self.gazebo_panel.clear_bbox_requested.connect(self.video_view.clear_drawn_bbox)
        self.gazebo_panel.start_tracking_requested.connect(self._call_start_tracking_latest)
        self.gazebo_panel.start_follow_requested.connect(self._call_start_follow)
        self.gazebo_panel.stop_follow_requested.connect(self._call_stop_follow)
        self.gazebo_panel.start_attack_requested.connect(self._call_start_attack)
        self.gazebo_panel.stop_attack_requested.connect(self._call_stop_attack)
        self.gazebo_panel.stop_tracking_requested.connect(self._call_stop_tracking)
        self.video_view.bbox_selected.connect(self._on_bbox_selected)
        self.video_view.resolution_changed.connect(self.camera_panel.set_stream_resolution)
        self.video_view.resolution_changed.connect(self.gazebo_panel.set_stream_resolution)
        self.video_view.status_changed.connect(self.update_status)

    def _toggle_split_view(self, enabled: bool) -> None:
        if enabled:
            self.video_view.show()
            total = max(self.left_splitter.height(), 2)
            half = total // 2
            self.left_splitter.setSizes([half, total - half])
            self._position_split_overlay_button()
            return
        self.video_view.hide()
        self.left_splitter.setSizes([1000, 0])
        self._position_split_overlay_button()

    def _on_panel_split_toggled(self, enabled: bool) -> None:
        if self.split_overlay_button.isChecked() != enabled:
            self.split_overlay_button.blockSignals(True)
            self.split_overlay_button.setChecked(enabled)
            self.split_overlay_button.blockSignals(False)
        self._toggle_split_view(enabled)

    def _on_overlay_split_toggled(self, enabled: bool) -> None:
        if self.panel.split_view_checkbox.isChecked() != enabled:
            self.panel.split_view_checkbox.blockSignals(True)
            self.panel.split_view_checkbox.setChecked(enabled)
            self.panel.split_view_checkbox.blockSignals(False)
        self._toggle_split_view(enabled)

    def _position_split_overlay_button(self) -> None:
        margin = 12
        size = self.split_overlay_button.sizeHint()
        x = max(margin, self.map_view.width() - size.width() - margin)
        y = margin
        self.split_overlay_button.move(x, y)
        self.split_overlay_button.raise_()

    def _apply_rtsp_stream(self, url: str, buffer_ms: int) -> None:
        url = url.strip()
        if not url:
            self.video_view.stop_stream()
            return
        # Camera tab needs OpenCV rendering when bbox drawing is enabled.
        # VLC/QVideoWidget path does not support interactive bbox overlay.
        if self.camera_panel.draw_bbox_checkbox.isChecked():
            self.video_view.open_gazebo_rtsp(url)
            self.update_status("Camera RTSP opened in bbox mode")
            return
        self.video_view.open_stream(url, buffer_ms=buffer_ms)

    def _on_camera_draw_toggled(self, enabled: bool) -> None:
        self.video_view.set_draw_enabled(enabled)
        # If user enables bbox while on Camera tab, switch RTSP to OpenCV path immediately.
        if not enabled:
            return
        if self.right_tabs.currentWidget() is not self.camera_panel:
            return
        rtsp_url = self.camera_panel.rtsp_input.text().strip()
        if not rtsp_url:
            return
        self.video_view.open_gazebo_rtsp(rtsp_url)
        self.update_status("Camera bbox mode enabled")

    def _apply_gazebo_stream(self, host: str, port: int) -> None:
        host = host.strip() or "0.0.0.0"
        self.video_view.open_gazebo_udp(host, int(port))

    def _apply_gazebo_rtsp_stream(self, url: str) -> None:
        url = url.strip()
        if not url:
            self.update_status("Gazebo RTSP URL is empty")
            return
        self.video_view.open_gazebo_rtsp(url)

    def _on_bbox_selected(self, payload: dict) -> None:
        self._latest_bbox_payload = payload
        bbox = payload.get("bbox", {})
        left = bbox.get("left", 0)
        top = bbox.get("top", 0)
        width = bbox.get("width", 0)
        height = bbox.get("height", 0)
        self.camera_panel.set_bbox_info(f"BBox: ({left},{top}) {width}x{height}")
        self.gazebo_panel.set_bbox_info(f"BBox: ({left},{top}) {width}x{height}")
        active = self.right_tabs.currentWidget()
        if active is self.camera_panel and self.camera_panel.auto_start_tracking_checkbox.isChecked():
            service = self.camera_panel.start_tracking_service_input.text().strip()
            self._call_start_tracking_with_bbox(service, payload)
        elif active is self.gazebo_panel and self.gazebo_panel.auto_start_tracking_checkbox.isChecked():
            service = self.gazebo_panel.start_tracking_service_input.text().strip()
            self._call_start_tracking_with_bbox(service, payload)
        self.video_view.clear_drawn_bbox()

    def _call_start_tracking_latest(self, service: str) -> None:
        if self._latest_bbox_payload is None:
            self.update_status("StartTracking skipped: no bbox yet")
            return
        self._call_start_tracking_with_bbox(service, self._latest_bbox_payload)

    def _call_start_tracking_with_bbox(self, service: str, payload: dict) -> None:
        service = service.strip()
        if not service:
            self.update_status("StartTracking failed: empty service name")
            return
        bbox = payload.get("bbox", {})
        w = int(bbox.get("width", 0))
        h = int(bbox.get("height", 0))
        if w <= 0 or h <= 0:
            self.update_status("StartTracking skipped: invalid bbox size")
            return
        x = int(bbox.get("left", 0))
        y = int(bbox.get("top", 0))
        args = {"bbox": {"x": x, "y": y, "w": w, "h": h}}
        ok = self.client.call_service(service, args)
        if ok:
            self.update_status(f"StartTracking called: {service} ({x},{y},{w},{h})")

    def _call_stop_tracking(self, service: str) -> None:
        service = service.strip()
        if not service:
            self.update_status("StopTracking failed: empty service name")
            return
        ok = self.client.call_service(service, {})
        if ok:
            self.update_status(f"StopTracking called: {service}")

    def _call_start_follow(self, service: str) -> None:
        service = service.strip()
        if not service:
            self.update_status("StartFollow failed: empty service name")
            return
        ok = self.client.call_service(service, {})
        if ok:
            self.update_status(f"StartFollow called: {service}")

    def _call_stop_follow(self, service: str) -> None:
        service = service.strip()
        if not service:
            self.update_status("StopFollow failed: empty service name")
            return
        ok = self.client.call_service(service, {})
        if ok:
            self.update_status(f"StopFollow called: {service}")

    def _call_start_attack(self, service: str) -> None:
        service = service.strip()
        if not service:
            self.update_status("StartAttack failed: empty service name")
            return
        ok = self.client.call_service(service, {})
        if ok:
            self.update_status(f"StartAttack called: {service}")

    def _call_stop_attack(self, service: str) -> None:
        service = service.strip()
        if not service:
            self.update_status("StopAttack failed: empty service name")
            return
        ok = self.client.call_service(service, {})
        if ok:
            self.update_status(f"StopAttack called: {service}")

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

    def eventFilter(self, obj, event):  # pragma: no cover
        if obj is self.map_view and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self._position_split_overlay_button()
        return super().eventFilter(obj, event)
