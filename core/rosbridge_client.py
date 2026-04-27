

import json
import threading
import uuid
from typing import Callable, Iterable, Optional

import websocket

MessageHandler = Callable[[str, dict], bool]
StatusHandler = Callable[[str], None]
DebugHandler = Callable[[str], None]


class RosbridgeClient:
    def __init__(
        self,
        url: str,
        topics: Iterable[str],
        on_message: MessageHandler,
        on_status: Optional[StatusHandler] = None,
        on_debug: Optional[DebugHandler] = None,
    ) -> None:
        self.url = url
        self.topics = list(topics)
        self.on_message = on_message
        self.on_status = on_status or (lambda _: None)
        self.on_debug = on_debug or (lambda _: None)
        self.debug_enabled = False
        self._app: Optional["websocket.WebSocketApp"] = None
        self._thread: Optional[threading.Thread] = None
        self._send_lock = threading.Lock()

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

    def publish(self, topic: str, msg: dict) -> bool:
        topic = topic.strip()
        if not topic:
            self.on_status("Publish failed: empty topic")
            return False
        if self._app is None:
            self.on_status("Publish failed: not connected")
            return False
        payload = {"op": "publish", "topic": topic, "msg": msg}
        try:
            with self._send_lock:
                self._app.send(json.dumps(payload, ensure_ascii=False))
            if self.debug_enabled:
                preview = json.dumps(payload, ensure_ascii=False)
                if len(preview) > 500:
                    preview = preview[:500] + "…"
                self.on_debug(f"TX {preview}")
            return True
        except Exception as exc:
            self.on_status(f"Publish failed: {exc}")
            return False

    def call_service(self, service: str, args: dict | None = None) -> bool:
        service = service.strip()
        if not service:
            self.on_status("Service call failed: empty service name")
            return False
        if self._app is None:
            self.on_status("Service call failed: not connected")
            return False
        payload = {
            "op": "call_service",
            "service": service,
            "args": args or {},
            "id": str(uuid.uuid4()),
        }
        try:
            with self._send_lock:
                self._app.send(json.dumps(payload, ensure_ascii=False))
            if self.debug_enabled:
                preview = json.dumps(payload, ensure_ascii=False)
                if len(preview) > 500:
                    preview = preview[:500] + "…"
                self.on_debug(f"TX {preview}")
            return True
        except Exception as exc:
            self.on_status(f"Service call failed: {exc}")
            return False

    def _handle_open(self, ws: "websocket.WebSocketApp") -> None:
        for topic in self.topics:
            ws.send(json.dumps({"op": "subscribe", "topic": topic}))
        topic_lines = "\n".join(self.topics)
        self.on_status(f"Subscribed:\n{topic_lines}")

    def _handle_raw_message(self, _ws: "websocket.WebSocketApp", raw: str) -> None:
        if self.debug_enabled:
            preview = raw if len(raw) <= 500 else raw[:500] + "…"
            self.on_debug(f"RX {preview}")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self.on_status("Ignored invalid JSON frame")
            if self.debug_enabled:
                self.on_debug("RX invalid JSON frame")
            return

        op = payload.get("op")
        if op == "service_response":
            if self.debug_enabled:
                self.on_debug(self._format_service_response(payload))
            return
        if op != "publish":
            if self.debug_enabled:
                self.on_debug(f"RX op={op}")
            return

        topic = payload.get("topic")
        msg = payload.get("msg", {})
        if not isinstance(topic, str) or not isinstance(msg, dict):
            if self.debug_enabled:
                self.on_debug("RX publish missing topic/msg")
            return

        handled = self.on_message(topic, msg)
        if self.debug_enabled:
            self.on_debug(f"publish {topic} handled={handled}")
            if handled:
                self.on_debug(self._format_debug(topic, msg))
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

    def _format_debug(self, topic: str, msg: dict) -> str:
        try:
            payload = json.dumps(msg, ensure_ascii=False)
        except (TypeError, ValueError):
            payload = str(msg)
        if len(payload) > 500:
            payload = payload[:500] + "…"
        return f"{topic} {payload}"

    def _format_service_response(self, payload: dict) -> str:
        service = payload.get("service", "")
        result = payload.get("result", False)
        values = payload.get("values", {})
        try:
            values_text = json.dumps(values, ensure_ascii=False)
        except Exception:
            values_text = str(values)
        if len(values_text) > 500:
            values_text = values_text[:500] + "…"
        return f"service_response service={service} result={result} values={values_text}"
