from __future__ import annotations

from dataclasses import dataclass

try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import (
        QCheckBox,
        QFormLayout,
        QFrame,
        QGridLayout,
        QGroupBox,
        QLabel,
        QLineEdit,
        QPushButton,
        QScrollArea,
        QSpinBox,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover
    from PySide6.QtCore import Qt, Signal as pyqtSignal
    from PySide6.QtWidgets import (
        QCheckBox,
        QFormLayout,
        QFrame,
        QGridLayout,
        QGroupBox,
        QLabel,
        QLineEdit,
        QPushButton,
        QScrollArea,
        QSpinBox,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )

try:
    from camera_ground.XF import camera_command
    from camera_ground.XF.gcu_controller import GCUController
except Exception as exc:  # pragma: no cover
    camera_command = None
    GCUController = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


@dataclass
class CameraConfig:
    ip: str
    port: int
    width: int
    height: int


class CollapsibleSection(QWidget):
    def __init__(self, title: str, content: QWidget, expanded: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._button = QToolButton()
        self._button.setText(title)
        self._button.setCheckable(True)
        self._button.setChecked(expanded)
        self._button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._button.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        self._button.setMinimumHeight(42)
        self._button.setStyleSheet(
            "QToolButton {"
            " color: #111111;"
            " background: #ffffff;"
            " font-weight: 600;"
            " text-align: left;"
            " padding: 6px 10px;"
            " border: 1px solid #d9d9d9;"
            " border-radius: 0px;"
            "}"
            "QToolButton:checked {"
            " background: #f5f5f5;"
            "}"
            "QToolButton:hover {"
            " background: #f2f2f2;"
            "}"
        )

        self._content = content
        self._content.setVisible(expanded)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._button)
        layout.addWidget(self._content)

        self._button.toggled.connect(self._on_toggled)

    def _on_toggled(self, opened: bool) -> None:
        self._content.setVisible(opened)
        self._button.setArrowType(Qt.ArrowType.DownArrow if opened else Qt.ArrowType.RightArrow)


class CameraControlPanel(QWidget):
    rtsp_apply_requested = pyqtSignal(str, int)
    draw_enabled_changed = pyqtSignal(bool)
    start_tracking_requested = pyqtSignal(str)
    start_follow_requested = pyqtSignal(str)
    stop_follow_requested = pyqtSignal(str)
    start_attack_requested = pyqtSignal(str)
    stop_attack_requested = pyqtSignal(str)
    stop_tracking_requested = pyqtSignal(str)
    clear_bbox_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller: object | None = None

        self.rtsp_input = QLineEdit("rtsp://192.168.50.73:8554/live/stream")
        self.buffer_input = QSpinBox()
        self.buffer_input.setRange(0, 10000)
        self.buffer_input.setValue(200)
        self.rtsp_apply_button = QPushButton("Apply RTSP")
        self.stream_resolution_label = QLabel("--")

        self.ip_input = QLineEdit("192.168.50.73")
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(9999)
        self.width_input = QSpinBox()
        self.width_input.setRange(1, 10000)
        self.width_input.setValue(1080)
        self.height_input = QSpinBox()
        self.height_input.setRange(1, 10000)
        self.height_input.setValue(720)

        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setEnabled(False)
        self.status_label = QLabel("Not connected")

        self.pitch_input = QLineEdit("0")
        self.yaw_input = QLineEdit("0")
        self.gimbal_button = QPushButton("Send Gimbal")

        self.reset_button = QPushButton("Reset")
        self.calibration_button = QPushButton("Calibration")
        self.lock_button = QPushButton("Lock")
        self.follow_button = QPushButton("Follow")
        self.down_button = QPushButton("Down")
        self.photo_button = QPushButton("Photo")
        self.video_button = QPushButton("Video")
        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_stop_button = QPushButton("Zoom Stop")
        self.digital_zoom_checkbox = QCheckBox("Digital Zoom")
        self.digital_zoom_checkbox.setChecked(True)
        self.digital_zoom_apply_button = QPushButton("Apply")
        self.zoom_set_input = QLineEdit("2.0")
        self.zoom_set_button = QPushButton("Zoom Set")
        self.focus_button = QPushButton("Focus")
        self.osd_on_button = QPushButton("OSD On")
        self.osd_off_button = QPushButton("OSD Off")
        self.laser_on_button = QPushButton("Laser On")
        self.laser_off_button = QPushButton("Laser Off")

        self.draw_bbox_checkbox = QCheckBox("Enable box drawing")
        self.draw_bbox_checkbox.setChecked(False)
        self.auto_start_tracking_checkbox = QCheckBox("Auto call /tracking/start on release")
        self.auto_start_tracking_checkbox.setChecked(True)
        self.start_tracking_service_input = QLineEdit("/tracking/start")
        self.stop_tracking_service_input = QLineEdit("/tracking/stop")
        self.start_follow_service_input = QLineEdit("/follow/start")
        self.stop_follow_service_input = QLineEdit("/follow/stop")
        self.start_attack_service_input = QLineEdit("/attack/start")
        self.stop_attack_service_input = QLineEdit("/attack/stop")
        self.start_tracking_button = QPushButton("Call Start Tracking")
        self.stop_tracking_button = QPushButton("Call Stop Tracking")
        self.start_follow_button = QPushButton("Call Start Follow")
        self.stop_follow_button = QPushButton("Call Stop Follow")
        self.start_attack_button = QPushButton("Call Start Attack")
        self.stop_attack_button = QPushButton("Call Stop Attack")
        self.clear_bbox_button = QPushButton("Clear BBox")
        self.bbox_info_label = QLabel("BBox: --")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: #ffffff; }")

        container = QWidget()
        container.setStyleSheet("background: #ffffff; color: #111111;")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(CollapsibleSection("Connect", self._build_connect_page(), expanded=True))
        container_layout.addWidget(CollapsibleSection("Gimbal & Camera Control", self._build_gimbal_page(), expanded=False))
        container_layout.addWidget(CollapsibleSection("Tracking System", self._build_tracking_page(), expanded=False))
        container_layout.addStretch(1)
        scroll.setWidget(container)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll)

        self.connect_button.clicked.connect(self._connect)
        self.disconnect_button.clicked.connect(self._disconnect)
        self.rtsp_apply_button.clicked.connect(self._apply_rtsp)
        self.gimbal_button.clicked.connect(self._send_gimbal)
        self.digital_zoom_apply_button.clicked.connect(self._apply_digital_zoom)
        self.zoom_set_button.clicked.connect(self._send_zoom_set)
        self.reset_button.clicked.connect(lambda: self._send_simple(camera_command.reset))
        self.calibration_button.clicked.connect(lambda: self._send_simple(camera_command.calibration))
        self.lock_button.clicked.connect(lambda: self._send_simple(camera_command.lock))
        self.follow_button.clicked.connect(lambda: self._send_simple(camera_command.follow))
        self.down_button.clicked.connect(lambda: self._send_simple(camera_command.down))
        self.photo_button.clicked.connect(lambda: self._send_simple(camera_command.photo))
        self.video_button.clicked.connect(lambda: self._send_simple(camera_command.video))
        self.zoom_in_button.clicked.connect(lambda: self._send_simple(camera_command.zoom_in))
        self.zoom_out_button.clicked.connect(lambda: self._send_simple(camera_command.zoom_out))
        self.zoom_stop_button.clicked.connect(lambda: self._send_simple(camera_command.zoom_stop))
        self.focus_button.clicked.connect(lambda: self._send_simple(camera_command.focus))
        self.osd_on_button.clicked.connect(lambda: self._send_simple(camera_command.osd_on))
        self.osd_off_button.clicked.connect(lambda: self._send_simple(camera_command.osd_off))
        self.laser_on_button.clicked.connect(lambda: self._send_simple(camera_command.laser_on))
        self.laser_off_button.clicked.connect(lambda: self._send_simple(camera_command.laser_off))

        self.draw_bbox_checkbox.toggled.connect(self.draw_enabled_changed.emit)
        self.start_tracking_button.clicked.connect(self._call_start_tracking)
        self.stop_tracking_button.clicked.connect(self._call_stop_tracking)
        self.clear_bbox_button.clicked.connect(self.clear_bbox_requested.emit)
        self.start_follow_button.clicked.connect(self._call_start_follow)
        self.stop_follow_button.clicked.connect(self._call_stop_follow)
        self.start_attack_button.clicked.connect(self._call_start_attack)
        self.stop_attack_button.clicked.connect(self._call_stop_attack)

        if _IMPORT_ERROR is not None:
            self._set_status(f"Camera modules not available: {_IMPORT_ERROR}")
            self._set_controls_enabled(False)

    def _build_connect_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout()
        form.addRow("RTSP URL", self.rtsp_input)
        form.addRow("Buffer (ms)", self.buffer_input)
        form.addRow("Resolution", self.stream_resolution_label)
        form.addRow("GCU IP", self.ip_input)
        form.addRow("Port", self.port_input)
        form.addRow("Width", self.width_input)
        form.addRow("Height", self.height_input)

        layout = QVBoxLayout(page)
        layout.addLayout(form)
        layout.addWidget(self.rtsp_apply_button)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.disconnect_button)
        layout.addWidget(self.status_label)
        return page

    def _build_gimbal_page(self) -> QWidget:
        page = QWidget()
        gimbal_group = QGroupBox("Gimbal")
        gimbal_layout = QGridLayout(gimbal_group)
        gimbal_layout.addWidget(QLabel("Pitch"), 0, 0)
        gimbal_layout.addWidget(self.pitch_input, 0, 1)
        gimbal_layout.addWidget(QLabel("Yaw"), 0, 2)
        gimbal_layout.addWidget(self.yaw_input, 0, 3)
        gimbal_layout.addWidget(self.gimbal_button, 1, 0, 1, 4)
        gimbal_layout.addWidget(self.digital_zoom_checkbox, 2, 0, 1, 3)
        gimbal_layout.addWidget(self.digital_zoom_apply_button, 2, 3)
        gimbal_layout.addWidget(QLabel("Zoom x"), 3, 0)
        gimbal_layout.addWidget(self.zoom_set_input, 3, 1, 1, 2)
        gimbal_layout.addWidget(self.zoom_set_button, 3, 3)

        action_group = QGroupBox("Actions")
        action_layout = QGridLayout(action_group)
        buttons = [
            self.reset_button,
            self.calibration_button,
            self.lock_button,
            self.follow_button,
            self.down_button,
            self.photo_button,
            self.video_button,
            self.zoom_in_button,
            self.zoom_out_button,
            self.zoom_stop_button,
            self.focus_button,
            self.osd_on_button,
            self.osd_off_button,
            self.laser_on_button,
            self.laser_off_button,
        ]
        for idx, button in enumerate(buttons):
            row = idx // 2
            col = idx % 2
            action_layout.addWidget(button, row, col)

        layout = QVBoxLayout(page)
        layout.addWidget(gimbal_group)
        layout.addWidget(action_group)
        return page

    def _build_tracking_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout()
        form.addRow("StartTracking Service", self.start_tracking_service_input)
        form.addRow("StopTracking Service", self.stop_tracking_service_input)
        form.addRow("StartFollow Service", self.start_follow_service_input)
        form.addRow("StopFollow Service", self.stop_follow_service_input)
        form.addRow("StartAttack Service", self.start_attack_service_input)
        form.addRow("StopAttack Service", self.stop_attack_service_input)

        image_group = QGroupBox("Image")
        image_layout = QVBoxLayout(image_group)
        image_layout.addWidget(self.start_tracking_button)
        image_layout.addWidget(self.stop_tracking_button)
        image_layout.addWidget(self.clear_bbox_button)

        control_group = QGroupBox("Control")
        control_layout = QVBoxLayout(control_group)
        control_layout.addWidget(self.start_follow_button)
        control_layout.addWidget(self.stop_follow_button)
        control_layout.addWidget(self.start_attack_button)
        control_layout.addWidget(self.stop_attack_button)

        layout = QVBoxLayout(page)
        layout.addWidget(self.draw_bbox_checkbox)
        layout.addWidget(self.auto_start_tracking_checkbox)
        layout.addLayout(form)
        layout.addWidget(image_group)
        layout.addWidget(control_group)
        layout.addWidget(self.bbox_info_label)
        return page

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_stream_resolution(self, text: str) -> None:
        self.stream_resolution_label.setText(text)

    def set_bbox_info(self, text: str) -> None:
        self.bbox_info_label.setText(text)

    def _apply_rtsp(self) -> None:
        url = self.rtsp_input.text().strip()
        buffer_ms = int(self.buffer_input.value())
        self.rtsp_apply_requested.emit(url, buffer_ms)
        if url:
            self._set_status(f"RTSP applied: {url} (buffer {buffer_ms} ms)")
        else:
            self._set_status("RTSP URL is empty")

    def _call_start_tracking(self) -> None:
        service = self.start_tracking_service_input.text().strip()
        self.start_tracking_requested.emit(service)

    def _call_start_follow(self) -> None:
        service = self.start_follow_service_input.text().strip()
        self.start_follow_requested.emit(service)

    def _call_stop_follow(self) -> None:
        service = self.stop_follow_service_input.text().strip()
        self.stop_follow_requested.emit(service)

    def _call_start_attack(self) -> None:
        service = self.start_attack_service_input.text().strip()
        self.start_attack_requested.emit(service)

    def _call_stop_attack(self) -> None:
        service = self.stop_attack_service_input.text().strip()
        self.stop_attack_requested.emit(service)

    def _call_stop_tracking(self) -> None:
        service = self.stop_tracking_service_input.text().strip()
        self.stop_tracking_requested.emit(service)

    def _set_controls_enabled(self, enabled: bool) -> None:
        for widget in [
            self.connect_button,
            self.disconnect_button,
            self.gimbal_button,
            self.reset_button,
            self.calibration_button,
            self.lock_button,
            self.follow_button,
            self.down_button,
            self.photo_button,
            self.video_button,
            self.zoom_in_button,
            self.zoom_out_button,
            self.zoom_stop_button,
            self.digital_zoom_checkbox,
            self.digital_zoom_apply_button,
            self.zoom_set_button,
            self.focus_button,
            self.osd_on_button,
            self.osd_off_button,
            self.laser_on_button,
            self.laser_off_button,
        ]:
            widget.setEnabled(enabled)

    def _connect(self) -> None:
        if GCUController is None:
            return
        if self._controller is not None:
            self._set_status("Already connected")
            return
        config = CameraConfig(
            ip=self.ip_input.text().strip(),
            port=int(self.port_input.value()),
            width=int(self.width_input.value()),
            height=int(self.height_input.value()),
        )
        try:
            self._controller = GCUController(config.ip, config.port, config.width, config.height)
            self._controller.connect()
        except Exception as exc:  # pragma: no cover
            self._controller = None
            self._set_status(f"Connect failed: {exc}")
            return
        self._set_status("Connected")
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)

    def _disconnect(self) -> None:
        if self._controller is None:
            return
        try:
            self._controller.disconnect()
        except Exception as exc:  # pragma: no cover
            self._set_status(f"Disconnect failed: {exc}")
        self._controller = None
        self._set_status("Disconnected")
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)

    def _send_gimbal(self) -> None:
        if self._controller is None or camera_command is None:
            self._set_status("Not connected")
            return
        try:
            pitch = float(self.pitch_input.text().strip())
            yaw = float(self.yaw_input.text().strip())
        except ValueError:
            self._set_status("Invalid pitch/yaw")
            return
        try:
            camera_command.control_gimbal(self._controller, pitch=pitch, yaw=yaw)
            self._set_status("Gimbal command sent")
        except Exception as exc:  # pragma: no cover
            self._set_status(f"Gimbal failed: {exc}")

    def _send_simple(self, func) -> None:
        if self._controller is None or camera_command is None:
            self._set_status("Not connected")
            return
        try:
            func(self._controller)
            self._set_status(f"Sent {func.__name__}")
        except Exception as exc:  # pragma: no cover
            self._set_status(f"{func.__name__} failed: {exc}")

    def _send_zoom_set(self) -> None:
        if self._controller is None or camera_command is None:
            self._set_status("Not connected")
            return
        try:
            zoom = float(self.zoom_set_input.text().strip())
        except ValueError:
            self._set_status("Invalid zoom value")
            return
        try:
            camera_command.zoom_set(self._controller, zoom=zoom)
            self._set_status(f"Sent zoom_set {zoom:.1f}x")
        except Exception as exc:  # pragma: no cover
            self._set_status(f"zoom_set failed: {exc}")

    def _apply_digital_zoom(self) -> None:
        if self._controller is None or camera_command is None:
            self._set_status("Not connected")
            return
        enabled = self.digital_zoom_checkbox.isChecked()
        try:
            camera_command.set_digital_zoom(self._controller, enable=enabled)
            self._set_status(f"Digital zoom {'ON' if enabled else 'OFF'}")
        except Exception as exc:  # pragma: no cover
            self._set_status(f"digital zoom failed: {exc}")
