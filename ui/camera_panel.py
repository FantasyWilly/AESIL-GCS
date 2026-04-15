from __future__ import annotations

from dataclasses import dataclass

try:
    from PyQt6.QtWidgets import (
        QCheckBox,
        QFormLayout,
        QGridLayout,
        QGroupBox,
        QLabel,
        QLineEdit,
        QPushButton,
        QSpinBox,
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
        QPushButton,
        QSpinBox,
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


class CameraControlPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller: object | None = None

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

        form = QFormLayout()
        form.addRow("GCU IP", self.ip_input)
        form.addRow("Port", self.port_input)
        form.addRow("Width", self.width_input)
        form.addRow("Height", self.height_input)

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

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.disconnect_button)
        layout.addWidget(self.status_label)
        layout.addWidget(gimbal_group)
        layout.addWidget(action_group)
        layout.addStretch(1)

        self.connect_button.clicked.connect(self._connect)
        self.disconnect_button.clicked.connect(self._disconnect)
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

        if _IMPORT_ERROR is not None:
            self._set_status(f"Camera modules not available: {_IMPORT_ERROR}")
            self._set_controls_enabled(False)

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

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
