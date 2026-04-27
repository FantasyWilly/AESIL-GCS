from __future__ import annotations

try:
    from PyQt6.QtCore import pyqtSignal
    from PyQt6.QtWidgets import (
        QCheckBox,
        QFormLayout,
        QGroupBox,
        QLabel,
        QPushButton,
        QSpinBox,
        QVBoxLayout,
        QWidget,
        QLineEdit,
    )
except ImportError:  # pragma: no cover
    from PySide6.QtCore import Signal as pyqtSignal
    from PySide6.QtWidgets import (
        QCheckBox,
        QFormLayout,
        QGroupBox,
        QLabel,
        QPushButton,
        QSpinBox,
        QVBoxLayout,
        QWidget,
        QLineEdit,
    )


class GazeboPanel(QWidget):
    gazebo_apply_requested = pyqtSignal(str, int)
    gazebo_rtsp_apply_requested = pyqtSignal(str)
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

        # Gazebo 
        self.gazebo_host_input = QLineEdit("0.0.0.0")
        self.gazebo_port_input = QSpinBox()
        self.gazebo_port_input.setRange(1, 65535)
        self.gazebo_port_input.setValue(5600)
        self.gazebo_rtsp_input = QLineEdit("rtsp://127.0.0.1:8554/live/stream")
        self.stream_resolution_label = QLabel("--")
        self.status_label = QLabel("Gazebo not applied")
        self.gazebo_apply_button = QPushButton("Apply Gazebo UDP")
        self.gazebo_rtsp_apply_button = QPushButton("Apply Gazebo RTSP")
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

        form = QFormLayout()
        form.addRow("Gazebo UDP Host", self.gazebo_host_input)
        form.addRow("Gazebo UDP Port", self.gazebo_port_input)
        form.addRow("Gazebo RTSP URL", self.gazebo_rtsp_input)
        form.addRow("Resolution", self.stream_resolution_label)
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

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.gazebo_apply_button)
        layout.addWidget(self.gazebo_rtsp_apply_button)
        layout.addWidget(self.draw_bbox_checkbox)
        layout.addWidget(self.auto_start_tracking_checkbox)
        layout.addWidget(image_group)
        layout.addWidget(control_group)
        layout.addWidget(self.bbox_info_label)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

        self.gazebo_apply_button.clicked.connect(self._apply_gazebo)
        self.gazebo_rtsp_apply_button.clicked.connect(self._apply_gazebo_rtsp)
        self.draw_bbox_checkbox.toggled.connect(self.draw_enabled_changed.emit)

        self.start_tracking_button.clicked.connect(self._call_start_tracking)
        self.stop_tracking_button.clicked.connect(self._call_stop_tracking)
        self.clear_bbox_button.clicked.connect(self.clear_bbox_requested.emit)

        self.start_follow_button.clicked.connect(self._call_start_follow)
        self.stop_follow_button.clicked.connect(self._call_stop_follow)
        self.start_attack_button.clicked.connect(self._call_start_attack)
        self.stop_attack_button.clicked.connect(self._call_stop_attack)

    def _apply_gazebo(self) -> None:
        host = self.gazebo_host_input.text().strip() or "0.0.0.0"
        port = int(self.gazebo_port_input.value())
        self.gazebo_apply_requested.emit(host, port)
        self.status_label.setText(f"Gazebo UDP applied: {host}:{port}")

    def _apply_gazebo_rtsp(self) -> None:
        url = self.gazebo_rtsp_input.text().strip()
        self.gazebo_rtsp_apply_requested.emit(url)
        if url:
            self.status_label.setText(f"Gazebo RTSP applied: {url}")
        else:
            self.status_label.setText("Gazebo RTSP URL is empty")

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

    def set_stream_resolution(self, text: str) -> None:
        self.stream_resolution_label.setText(text)

    def set_bbox_info(self, text: str) -> None:
        self.bbox_info_label.setText(text)
