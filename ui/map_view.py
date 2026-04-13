from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

try:
    from PyQt6.QtCore import QUrl
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtWebEngineCore import QWebEngineSettings
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWidgets import QStackedLayout, QTextBrowser, QWidget
except ImportError:  # pragma: no cover
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QPixmap
    from PySide6.QtWebEngineCore import QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWidgets import QStackedLayout, QTextBrowser, QWidget

from core.state import AppState


class MapView(QWidget):
    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self._page_loaded = False
        self._last_payload = ""
        self._offline_tile_template = "http://127.0.0.1:8765/tiles/offline/{z}/{x}/{y}"
        self._offline_map_info: dict[str, Any] = {}
        self._html_path = Path(__file__).resolve().parent / "assets" / "map_view.html"

        self.browser = QWebEngineView(self)
        self.browser.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            True,
        )
        self.browser.loadFinished.connect(self._handle_load_finished)
        self.browser.setUrl(QUrl.fromLocalFile(str(self._html_path)))

        self.fallback = QTextBrowser(self)
        self.fallback.setReadOnly(True)
        self.fallback.setOpenExternalLinks(False)
        self.fallback.setPlainText("Map loading...")

        layout = QStackedLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.browser)
        layout.addWidget(self.fallback)
        layout.setCurrentWidget(self.browser)

        self.setMinimumSize(720, 520)

    def save_image(self, file_path: str | Path) -> Path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pixmap: QPixmap = self.grab()
        pixmap.save(str(path), "PNG")
        return path

    def sync_state(self) -> None:
        payload = self._build_payload()
        payload_json = json.dumps(payload, ensure_ascii=False)
        if not self._page_loaded or payload_json == self._last_payload:
            return
        self._last_payload = payload_json
        script = f"window.mapApi && window.mapApi.renderState({payload_json});"
        self.browser.page().runJavaScript(script)

    def set_offline_tile_template(self, template: str) -> None:
        self._offline_tile_template = template
        if not self._page_loaded:
            return
        script = f"window.mapApi && window.mapApi.setOfflineTileTemplate({json.dumps(template)});"
        self.browser.page().runJavaScript(script)

    def set_offline_map_info(self, info: dict[str, Any]) -> None:
        self._offline_map_info = info
        if not self._page_loaded:
            return
        script = f"window.mapApi && window.mapApi.setOfflineMapInfo({json.dumps(info, ensure_ascii=False)});"
        self.browser.page().runJavaScript(script)

    def reload_offline_map(self) -> None:
        if not self._page_loaded:
            return
        self.browser.page().runJavaScript("window.mapApi && window.mapApi.reloadOfflineMap();")

    def reset_view_to_offline_bounds(self) -> None:
        if not self._page_loaded:
            return
        self.browser.page().runJavaScript("window.mapApi && window.mapApi.resetViewToOfflineBounds();")

    def _handle_load_finished(self, ok: bool) -> None:
        self._page_loaded = ok
        if ok:
            self.set_offline_tile_template(self._offline_tile_template)
            self.set_offline_map_info(self._offline_map_info)
            self.sync_state()
            return
        self.fallback.setPlainText(f"Failed to load map HTML:\n{self._html_path}")

    def _build_payload(self) -> Dict[str, Any]:
        aircraft = self.state.snapshot_aircraft()
        track = self.state.snapshot_track()
        targets = self.state.snapshot_targets()

        return {
            "aircraft": self._point_to_dict(aircraft.point, label="Aircraft") if aircraft else None,
            "track": [self._point_to_dict(sample.point) for sample in track],
            "targets": [
                {
                    "tracker_id": target.tracker_id,
                    "vehicle_name": target.vehicle_name,
                    "position": self._point_to_dict(target.position),
                }
                for target in targets.values()
            ],
        }

    def _point_to_dict(self, point, label: str | None = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "latitude": point.latitude,
            "longitude": point.longitude,
            "altitude": point.altitude,
        }
        if label:
            payload["label"] = label
        return payload
