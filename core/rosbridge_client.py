

import json
import threading
from typing import Callable, Iterable, Optional

import websocket

MessageHandler = Callable[[str, dict], bool]
StatusHandler = Callable[[str], None]


class RosbridgeClient:
    def __init__(
        self,
        url: str,
        topics: Iterable[str],
        on_message: MessageHandler,
        on_status: Optional[StatusHandler] = None,
    ) -> None:
        self.url = url
        self.topics = list(topics)
        self.on_message = on_message
        self.on_status = on_status or (lambda _: None)
        self._app: Optional["websocket.WebSocketApp"] = None
        self._thread: Optional[threading.Thread] = None

    def connect(self) -> None:
        if websocket is None:
            raise RuntimeError("Missing dependency: websocket-client")
        if self._thread and self._thread.is_alive():
            return

        self._app = websocket.WebSocketApp(
            self.url,
            on_open=self._handle_open,
            on_message=self._handle_raw_message,
            on_error=self._handle_error,
            on_close=self._handle_close,
        )
        self._thread = threading.Thread(target=self._app.run_forever, daemon=True)
        self._thread.start()
        self.on_status(f"Connecting to {self.url}")

    def disconnect(self) -> None:
        if self._app is not None:
            self._app.close()
            self._app = None
        self._thread = None
        self.on_status("Disconnected")

    def _handle_open(self, ws: "websocket.WebSocketApp") -> None:
        for topic in self.topics:
            ws.send(json.dumps({"op": "subscribe", "topic": topic}))
        topic_lines = "\n".join(self.topics)
        self.on_status(f"Subscribed:\n{topic_lines}")

    def _handle_raw_message(self, _ws: "websocket.WebSocketApp", raw: str) -> None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self.on_status("Ignored invalid JSON frame")
            return

        if payload.get("op") != "publish":
            return

        topic = payload.get("topic")
        msg = payload.get("msg", {})
        if not isinstance(topic, str) or not isinstance(msg, dict):
            return

        handled = self.on_message(topic, msg)
        if handled:
            self.on_status(f"Updated from {topic}")

    def _handle_error(self, _ws: "websocket.WebSocketApp", error: object) -> None:
        self.on_status(f"ROSBridge error: {error}")

    def _handle_close(
        self,
        _ws: "websocket.WebSocketApp",
        status_code: object,
        message: object,
    ) -> None:
        self._app = None
        self._thread = None
        self.on_status(f"Connection closed ({status_code}): {message}")
