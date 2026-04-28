from __future__ import annotations

import socket
import sys
import time

try:
    from PyQt6.QtCore import QPoint, QRect, Qt, QTimer, QUrl, pyqtSignal
    from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
    from PyQt6.QtMultimedia import QMediaPlayer
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    from PyQt6.QtWidgets import QLabel, QStackedLayout, QWidget
except ImportError:  # pragma: no cover
    from PySide6.QtCore import QPoint, QRect, Qt, QTimer, QUrl, Signal as pyqtSignal
    from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
    from PySide6.QtMultimedia import QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget

try:
    import vlc
except Exception:  # pragma: no cover
    vlc = None

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None


class InteractiveFrameLabel(QLabel):
    pressed = pyqtSignal(QPoint)
    moved = pyqtSignal(QPoint)
    released = pyqtSignal(QPoint)

    def mousePressEvent(self, event) -> None:  # pragma: no cover
        if event.button() == Qt.MouseButton.LeftButton:
            self.pressed.emit(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # pragma: no cover
        self.moved.emit(event.position().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # pragma: no cover
        if event.button() == Qt.MouseButton.LeftButton:
            self.released.emit(event.position().toPoint())
        super().mouseReleaseEvent(event)


class VideoStreamWidget(QWidget):
    resolution_changed = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    bbox_selected = pyqtSignal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._url = ""
        self._buffer_ms = 200
        self._stream_source = "none"
        self._draw_enabled = False
        self._frame_width = 0
        self._frame_height = 0
        self._display_rect = QRect()
        self._source_pixmap: QPixmap | None = None
        self._anchor_point: tuple[int, int] | None = None
        self._current_point: tuple[int, int] | None = None
        self._bbox_corners: list[tuple[int, int]] | None = None

        self.video_widget = QVideoWidget(self)
        self.video_widget.setStyleSheet("background-color: #000000;")
        self.frame_widget = InteractiveFrameLabel(self)
        self.frame_widget.setStyleSheet("background-color: #000000;")
        self.frame_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder = QLabel("No video stream")
        self.placeholder.setStyleSheet("background-color: #000000; color: #9ca3af; font-size: 20px;")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QStackedLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setStackingMode(QStackedLayout.StackingMode.StackOne)
        layout.addWidget(self.video_widget)
        layout.addWidget(self.frame_widget)
        layout.addWidget(self.placeholder)
        self._stack = layout
        self._stack.setCurrentWidget(self.placeholder)

        self.player = QMediaPlayer(self)
        self.player.setVideoOutput(self.video_widget)
        self.player.errorOccurred.connect(self._on_error_qt)

        self._vlc_instance = None
        self._vlc_player = None
        self._opencv_capture = None
        self._size_timer = QTimer(self)
        self._size_timer.setInterval(1000)
        self._size_timer.timeout.connect(self._poll_vlc_resolution)
        self._opencv_timer = QTimer(self)
        self._opencv_timer.setInterval(33)
        self._opencv_timer.timeout.connect(self._poll_opencv_frame)

        self.frame_widget.pressed.connect(self._on_frame_mouse_press)
        self.frame_widget.moved.connect(self._on_frame_mouse_move)
        self.frame_widget.released.connect(self._on_frame_mouse_release)

        try:
            sink = self.video_widget.videoSink()
            sink.videoFrameChanged.connect(self._on_frame_changed)
        except Exception:  # pragma: no cover
            pass

    def open_stream(self, url: str, buffer_ms: int = 200) -> None:
        self._url = url.strip()
        self._buffer_ms = max(0, int(buffer_ms))
        if not self._url:
            self.status_changed.emit("RTSP URL is empty")
            self._stack.setCurrentWidget(self.placeholder)
            return
        if vlc is not None:
            self._open_with_vlc()
            return
        self._open_with_qt_fallback()

    def stop_stream(self) -> None:
        self._size_timer.stop()
        self._opencv_timer.stop()
        self._cleanup_opencv()
        self._cleanup_vlc()
        self.player.stop()
        self.frame_widget.clear()
        self._source_pixmap = None
        self._stream_source = "none"
        self.clear_drawn_bbox()
        self._stack.setCurrentWidget(self.placeholder)
        self.resolution_changed.emit("--")
        self.status_changed.emit("Video stopped")

    def set_draw_enabled(self, enabled: bool) -> None:
        self._draw_enabled = enabled
        if not enabled:
            self._anchor_point = None
            self._current_point = None
            self._refresh_overlay()

    def clear_drawn_bbox(self) -> None:
        self._anchor_point = None
        self._current_point = None
        self._bbox_corners = None
        self._refresh_overlay()

    @staticmethod
    def _build_udp_gst_pipeline(udp_host: str, udp_port: int) -> str:
        return (
            f"udpsrc address={udp_host} port={udp_port} "
            "caps=application/x-rtp,media=video,encoding-name=H264,clock-rate=90000 ! "
            "rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! "
            "appsink drop=true sync=false"
        )

    def open_gazebo_udp(self, udp_host: str, udp_port: int) -> None:
        if cv2 is None:
            self.status_changed.emit("Gazebo UDP requires OpenCV (cv2) with GStreamer support")
            self._stack.setCurrentWidget(self.placeholder)
            return
        self.player.stop()
        self._cleanup_vlc()
        self._cleanup_opencv()
        has_packets = self._probe_udp_packets(udp_host, int(udp_port), timeout_ms=600)
        if not has_packets:
            self.status_changed.emit(
                f"Gazebo UDP waiting packets on {udp_host}:{udp_port} (source not started yet)"
            )
            self._stack.setCurrentWidget(self.placeholder)
            return
        pipeline = self._build_udp_gst_pipeline(udp_host, int(udp_port))
        self._opencv_capture = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if not self._opencv_capture.isOpened():
            self._cleanup_opencv()
            self.status_changed.emit(
                f"Gazebo UDP open failed: {udp_host}:{udp_port} (check GStreamer/OpenCV build)"
            )
            self._stack.setCurrentWidget(self.placeholder)
            return
        self._opencv_timer.start()
        self._stack.setCurrentWidget(self.frame_widget)
        self._stream_source = "gazebo_udp"
        self.status_changed.emit(f"Gazebo UDP streaming: {udp_host}:{udp_port}")

    def open_gazebo_rtsp(self, url: str) -> None:
        if cv2 is None:
            self.status_changed.emit("Gazebo RTSP requires OpenCV (cv2)")
            self._stack.setCurrentWidget(self.placeholder)
            return
        rtsp_url = url.strip()
        if not rtsp_url:
            self.status_changed.emit("Gazebo RTSP URL is empty")
            self._stack.setCurrentWidget(self.placeholder)
            return
        self.player.stop()
        self._cleanup_vlc()
        self._cleanup_opencv()
        self._opencv_capture = cv2.VideoCapture(rtsp_url)
        if not self._opencv_capture.isOpened():
            self._cleanup_opencv()
            self.status_changed.emit(f"Gazebo RTSP open failed: {rtsp_url}")
            self._stack.setCurrentWidget(self.placeholder)
            return
        self._opencv_timer.start()
        self._stack.setCurrentWidget(self.frame_widget)
        self._stream_source = "gazebo_rtsp"
        self.status_changed.emit(f"Gazebo RTSP streaming: {rtsp_url}")

    def open_camera_rtsp_gstreamer(self, url: str) -> None:
        if cv2 is None:
            self.status_changed.emit("Camera RTSP requires OpenCV (cv2) with GStreamer support")
            self._stack.setCurrentWidget(self.placeholder)
            return
        rtsp_url = url.strip()
        if not rtsp_url:
            self.status_changed.emit("Camera RTSP URL is empty")
            self._stack.setCurrentWidget(self.placeholder)
            return
        self.player.stop()
        self._cleanup_vlc()
        self._cleanup_opencv()
        pipeline = (
            f"rtspsrc location={rtsp_url} latency=50 protocols=tcp ! "
            "rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! "
            "appsink drop=true sync=false"
        )
        self._opencv_capture = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if not self._opencv_capture.isOpened():
            self._cleanup_opencv()
            # fallback: some builds can open RTSP URL directly but not rtspsrc pipeline
            self._opencv_capture = cv2.VideoCapture(rtsp_url)
            if not self._opencv_capture.isOpened():
                self._cleanup_opencv()
                self.status_changed.emit(f"Camera RTSP open failed: {rtsp_url}")
                self._stack.setCurrentWidget(self.placeholder)
                return
        self._opencv_timer.start()
        self._stack.setCurrentWidget(self.frame_widget)
        self._stream_source = "camera_rtsp"
        self.status_changed.emit(f"Camera RTSP (OpenCV+GStreamer) streaming: {rtsp_url}")

    @staticmethod
    def _probe_udp_packets(udp_host: str, udp_port: int, timeout_ms: int = 600) -> bool:
        bind_host = udp_host.strip() or "0.0.0.0"
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((bind_host, int(udp_port)))
            sock.settimeout(max(timeout_ms / 1000.0, 0.1))
            data, _ = sock.recvfrom(2048)
            return bool(data)
        except Exception:
            return False
        finally:
            try:
                sock.close()
            except Exception:
                pass

    def _open_with_vlc(self) -> None:
        self._opencv_timer.stop()
        self._cleanup_opencv()
        self.player.stop()
        self._cleanup_vlc()
        options = [f"--network-caching={self._buffer_ms}", "--no-video-title-show", "--rtsp-tcp"]
        self._vlc_instance = vlc.Instance(*options)
        self._vlc_player = self._vlc_instance.media_player_new()
        media = self._vlc_instance.media_new(self._url)
        self._vlc_player.set_media(media)
        wid = int(self.video_widget.winId())
        if sys.platform.startswith("linux"):
            self._vlc_player.set_xwindow(wid)
        elif sys.platform == "win32":
            self._vlc_player.set_hwnd(wid)
        elif sys.platform == "darwin":
            self._vlc_player.set_nsobject(wid)
        self._vlc_player.play()
        self._stack.setCurrentWidget(self.video_widget)
        self._size_timer.start()
        self._stream_source = "camera_rtsp"
        self.status_changed.emit(f"RTSP (VLC) streaming: {self._url} | buffer {self._buffer_ms} ms")

    def _open_with_qt_fallback(self) -> None:
        self._opencv_timer.stop()
        self._cleanup_opencv()
        self._cleanup_vlc()
        self.player.setSource(QUrl(self._url))
        self.player.play()
        self._stack.setCurrentWidget(self.video_widget)
        self._stream_source = "camera_rtsp"
        self.status_changed.emit(f"RTSP (Qt fallback) streaming: {self._url} | buffer option requires python-vlc")

    def _on_error_qt(self, *_args) -> None:
        error_text = self.player.errorString() or "Unknown media error"
        self.status_changed.emit(f"Video error: {error_text}")
        self._stack.setCurrentWidget(self.placeholder)
        self.resolution_changed.emit("--")

    def _on_frame_changed(self, frame) -> None:  # pragma: no cover
        try:
            size = frame.size()
            width, height = size.width(), size.height()
            if width > 0 and height > 0:
                self.resolution_changed.emit(f"{width} x {height}")
        except Exception:
            pass

    def _poll_vlc_resolution(self) -> None:
        if self._vlc_player is None:
            return
        try:
            width, height = self._vlc_player.video_get_size(0)
        except Exception:
            return
        if width > 0 and height > 0:
            self.resolution_changed.emit(f"{width} x {height}")

    def _cleanup_vlc(self) -> None:
        if self._vlc_player is not None:
            try:
                self._vlc_player.stop()
                self._vlc_player.release()
            except Exception:
                pass
            self._vlc_player = None
        if self._vlc_instance is not None:
            try:
                self._vlc_instance.release()
            except Exception:
                pass
            self._vlc_instance = None

    def _cleanup_opencv(self) -> None:
        if self._opencv_capture is not None:
            try:
                self._opencv_capture.release()
            except Exception:
                pass
            self._opencv_capture = None

    def _poll_opencv_frame(self) -> None:
        if self._opencv_capture is None:
            return
        ok, frame = self._opencv_capture.read()
        if not ok or frame is None:
            return
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, _ = rgb.shape
            self._frame_width = width
            self._frame_height = height
            image = QImage(rgb.data, width, height, width * 3, QImage.Format.Format_RGB888).copy()
            self._source_pixmap = QPixmap.fromImage(image)
            self._refresh_overlay()
            self.resolution_changed.emit(f"{width} x {height}")
        except Exception:
            pass

    def _refresh_overlay(self) -> None:
        if self._source_pixmap is None:
            return
        content_rect = self.frame_widget.contentsRect()
        if content_rect.width() <= 0 or content_rect.height() <= 0:
            return
        scaled = self._source_pixmap.scaled(
            content_rect.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x_offset = content_rect.x() + (content_rect.width() - scaled.width()) // 2
        y_offset = content_rect.y() + (content_rect.height() - scaled.height()) // 2
        self._display_rect = QRect(x_offset, y_offset, scaled.width(), scaled.height())
        if self._draw_enabled:
            painter = QPainter(scaled)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self._draw_bbox_overlay(painter)
            painter.end()
        self.frame_widget.setPixmap(scaled)

    def _draw_bbox_overlay(self, painter: QPainter) -> None:
        corners = self._bbox_corners
        if self._anchor_point and self._current_point:
            corners = self._build_corners(self._anchor_point, self._current_point)
        if not corners or self._frame_width <= 0 or self._frame_height <= 0:
            return
        display_points = [self._source_to_scaled(x, y) for x, y in corners]
        pen = QPen(QColor("#ffcc00"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QColor("#ffcc00"))
        for idx in range(4):
            painter.drawLine(display_points[idx], display_points[(idx + 1) % 4])
        for pt in display_points:
            painter.drawEllipse(pt, 4, 4)

    def _on_frame_mouse_press(self, pos: QPoint) -> None:
        if not self._draw_enabled:
            return
        source = self._widget_to_source(pos, clamp=False)
        if source is None:
            return
        self._anchor_point = source
        self._current_point = source
        self._refresh_overlay()

    def _on_frame_mouse_move(self, pos: QPoint) -> None:
        if not self._draw_enabled or self._anchor_point is None:
            return
        source = self._widget_to_source(pos, clamp=True)
        if source is None:
            return
        self._current_point = source
        self._refresh_overlay()

    def _on_frame_mouse_release(self, pos: QPoint) -> None:
        if not self._draw_enabled or self._anchor_point is None:
            return
        source = self._widget_to_source(pos, clamp=True)
        if source is None:
            self._anchor_point = None
            self._current_point = None
            self._refresh_overlay()
            return
        self._current_point = source
        corners = self._build_corners(self._anchor_point, self._current_point)
        self._bbox_corners = corners
        self._anchor_point = None
        self._current_point = None
        self._refresh_overlay()
        self.bbox_selected.emit(self._build_bbox_payload(corners))

    def _widget_to_source(self, pos: QPoint, clamp: bool) -> tuple[int, int] | None:
        if self._display_rect.width() <= 0 or self._display_rect.height() <= 0:
            return None
        px = pos.x()
        py = pos.y()
        if not self._display_rect.contains(pos):
            if not clamp:
                return None
            px = min(max(px, self._display_rect.left()), self._display_rect.right())
            py = min(max(py, self._display_rect.top()), self._display_rect.bottom())
        x = px - self._display_rect.x()
        y = py - self._display_rect.y()
        src_x = int(round(x * self._frame_width / self._display_rect.width()))
        src_y = int(round(y * self._frame_height / self._display_rect.height()))
        src_x = max(0, min(self._frame_width - 1, src_x))
        src_y = max(0, min(self._frame_height - 1, src_y))
        return src_x, src_y

    def _source_to_display(self, x: int, y: int) -> QPoint:
        dx = int(round(x * self._display_rect.width() / max(self._frame_width, 1)))
        dy = int(round(y * self._display_rect.height() / max(self._frame_height, 1)))
        return QPoint(self._display_rect.x() + dx, self._display_rect.y() + dy)

    def _source_to_scaled(self, x: int, y: int) -> QPoint:
        dx = int(round(x * self._display_rect.width() / max(self._frame_width, 1)))
        dy = int(round(y * self._display_rect.height() / max(self._frame_height, 1)))
        return QPoint(dx, dy)

    @staticmethod
    def _build_corners(p1: tuple[int, int], p2: tuple[int, int]) -> list[tuple[int, int]]:
        x1, y1 = p1
        x2, y2 = p2
        left = min(x1, x2)
        right = max(x1, x2)
        top = min(y1, y2)
        bottom = max(y1, y2)
        return [(left, top), (right, top), (right, bottom), (left, bottom)]

    def _build_bbox_payload(self, corners: list[tuple[int, int]]) -> dict:
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = corners
        left = min(x1, x2, x3, x4)
        right = max(x1, x2, x3, x4)
        top = min(y1, y2, y3, y4)
        bottom = max(y1, y2, y3, y4)
        return {
            "stamp_ms": int(time.time() * 1000),
            "source": self._stream_source,
            "image_size": {"width": self._frame_width, "height": self._frame_height},
            "corners": [
                {"name": "p1", "x": x1, "y": y1},
                {"name": "p2", "x": x2, "y": y2},
                {"name": "p3", "x": x3, "y": y3},
                {"name": "p4", "x": x4, "y": y4},
            ],
            "bbox": {
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "width": right - left,
                "height": bottom - top,
                "center_x": (left + right) / 2.0,
                "center_y": (top + bottom) / 2.0,
            },
        }

    def resizeEvent(self, event) -> None:  # pragma: no cover
        super().resizeEvent(event)
        self._refresh_overlay()
