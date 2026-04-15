from __future__ import annotations

import sys

try:
    from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
    from PyQt6.QtMultimedia import QMediaPlayer
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    from PyQt6.QtWidgets import QLabel, QStackedLayout, QWidget
except ImportError:  # pragma: no cover
    from PySide6.QtCore import Qt, QTimer, QUrl, Signal as pyqtSignal
    from PySide6.QtMultimedia import QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget

try:
    import vlc
except Exception:  # pragma: no cover
    vlc = None


class VideoStreamWidget(QWidget):
    resolution_changed = pyqtSignal(str)
    status_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._url = ""
        self._buffer_ms = 300

        self.video_widget = QVideoWidget(self)
        self.video_widget.setStyleSheet("background-color: #000000;")
        self.placeholder = QLabel("No video stream")
        self.placeholder.setStyleSheet("background-color: #000000; color: #9ca3af; font-size: 20px;")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QStackedLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setStackingMode(QStackedLayout.StackingMode.StackOne)
        layout.addWidget(self.video_widget)
        layout.addWidget(self.placeholder)
        self._stack = layout
        self._stack.setCurrentWidget(self.placeholder)

        self.player = QMediaPlayer(self)  # fallback backend
        self.player.setVideoOutput(self.video_widget)
        self.player.errorOccurred.connect(self._on_error_qt)

        self._vlc_instance = None
        self._vlc_player = None
        self._size_timer = QTimer(self)
        self._size_timer.setInterval(1000)
        self._size_timer.timeout.connect(self._poll_vlc_resolution)

        try:
            sink = self.video_widget.videoSink()
            sink.videoFrameChanged.connect(self._on_frame_changed)
        except Exception:  # pragma: no cover
            pass

    def open_stream(self, url: str, buffer_ms: int = 300) -> None:
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
        self._cleanup_vlc()
        self.player.stop()
        self._stack.setCurrentWidget(self.placeholder)
        self.resolution_changed.emit("--")
        self.status_changed.emit("Video stopped")

    def _open_with_vlc(self) -> None:
        self.player.stop()
        self._cleanup_vlc()
        options = [
            f"--network-caching={self._buffer_ms}",
            "--no-video-title-show",
            "--rtsp-tcp",
        ]
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
        self.status_changed.emit(f"RTSP (VLC) streaming: {self._url} | buffer {self._buffer_ms} ms")

    def _open_with_qt_fallback(self) -> None:
        self._cleanup_vlc()
        self.player.setSource(QUrl(self._url))
        self.player.play()
        self._stack.setCurrentWidget(self.video_widget)
        self.status_changed.emit(
            f"RTSP (Qt fallback) streaming: {self._url} | buffer option requires python-vlc"
        )

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
