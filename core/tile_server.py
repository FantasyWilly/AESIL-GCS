from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class OfflineMapSource:
    mbtiles_path: Optional[Path] = None
    name: str = "No offline map loaded"
    format: str = "png"
    bounds: tuple[float, float, float, float] | None = None
    center: tuple[float, float, int] | None = None
    minzoom: int | None = None
    maxzoom: int | None = None


class TileServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.host = host
        self.port = port
        self.source = OfflineMapSource()
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

    @property
    def offline_tile_template(self) -> str:
        return f"http://{self.host}:{self.port}/tiles/offline/{{z}}/{{x}}/{{y}}"

    def start(self) -> None:
        if self._httpd is not None:
            return

        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                try:
                    server._handle_request(self)
                except BrokenPipeError:
                    return

            def log_message(self, _format: str, *_args) -> None:
                return

        self._httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is None:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        self._httpd = None
        self._thread = None

    def set_mbtiles(self, file_path: str | Path) -> None:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)

        with sqlite3.connect(path) as connection:
            metadata_rows = dict(connection.execute("SELECT name, value FROM metadata"))
        tile_format = metadata_rows.get("format", "png").lower()
        if tile_format == "jpg":
            tile_format = "jpeg"

        with self._lock:
            self.source = OfflineMapSource(
                mbtiles_path=path,
                name=metadata_rows.get("name", path.stem),
                format=tile_format,
                bounds=self._parse_bounds(metadata_rows.get("bounds")),
                center=self._parse_center(metadata_rows.get("center")),
                minzoom=self._parse_int(metadata_rows.get("minzoom")),
                maxzoom=self._parse_int(metadata_rows.get("maxzoom")),
            )

    def get_source_info(self) -> dict:
        with self._lock:
            return {
                "loaded": self.source.mbtiles_path is not None,
                "name": self.source.name,
                "path": str(self.source.mbtiles_path) if self.source.mbtiles_path else "",
                "format": self.source.format,
                "bounds": self.source.bounds,
                "center": self.source.center,
                "minzoom": self.source.minzoom,
                "maxzoom": self.source.maxzoom,
            }

    def _handle_request(self, handler: BaseHTTPRequestHandler) -> None:
        path = handler.path.split("?", 1)[0]
        if path == "/status":
            self._write_json(handler, self.get_source_info())
            return

        prefix = "/tiles/offline/"
        if not path.startswith(prefix):
            handler.send_error(HTTPStatus.NOT_FOUND)
            return

        parts = path[len(prefix):].strip("/").split("/")
        if len(parts) != 3:
            handler.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            z = int(parts[0])
            x = int(parts[1])
            y = int(parts[2].split(".", 1)[0])
        except ValueError:
            handler.send_error(HTTPStatus.BAD_REQUEST)
            return

        with self._lock:
            source = self.source

        if source.mbtiles_path is None:
            handler.send_error(HTTPStatus.NOT_FOUND, "No MBTiles loaded")
            return

        tms_y = (2**z - 1) - y
        tile_data = self._read_tile(source.mbtiles_path, z, x, tms_y)
        if tile_data is None:
            handler.send_error(HTTPStatus.NOT_FOUND, "Tile not found")
            return

        content_type = "image/jpeg" if source.format in {"jpg", "jpeg"} else "image/png"
        handler.send_response(HTTPStatus.OK)
        handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Length", str(len(tile_data)))
        handler.send_header("Cache-Control", "public, max-age=3600")
        handler.end_headers()
        handler.wfile.write(tile_data)

    def _read_tile(self, mbtiles_path: Path, z: int, x: int, tms_y: int) -> bytes | None:
        with sqlite3.connect(mbtiles_path) as connection:
            row = connection.execute(
                """
                SELECT tile_data
                FROM tiles
                WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?
                """,
                (z, x, tms_y),
            ).fetchone()
        return bytes(row[0]) if row else None

    def _write_json(self, handler: BaseHTTPRequestHandler, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        handler.send_response(HTTPStatus.OK)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)

    def _parse_bounds(self, value: str | None) -> tuple[float, float, float, float] | None:
        if not value:
            return None
        try:
            west, south, east, north = [float(part) for part in value.split(",")]
        except ValueError:
            return None
        return (west, south, east, north)

    def _parse_center(self, value: str | None) -> tuple[float, float, int] | None:
        if not value:
            return None
        try:
            lon, lat, zoom = value.split(",")
            return (float(lon), float(lat), int(float(zoom)))
        except ValueError:
            return None

    def _parse_int(self, value: str | None) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None
