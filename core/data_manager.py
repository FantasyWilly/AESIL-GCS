from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.logger import DataLogger
from core.state import AppState, FlightSample, GeoPoint, TargetRecord

# 數據管理器
class DataManager:
    AIRCRAFT_TOPIC = "/mavros/global_position/raw/fix"
    TARGET_TOPIC = "/external/target_position"

    def __init__(self, state: AppState, logger: DataLogger) -> None:
        self.state = state
        self.logger = logger

    def handle_message(self, topic: str, message: Dict[str, Any]) -> bool:
        if topic == self.AIRCRAFT_TOPIC:
            return self._handle_aircraft(message)
        if topic == self.TARGET_TOPIC:
            return self._handle_target(message)
        return False

    def _handle_aircraft(self, message: Dict[str, Any]) -> bool:
        latitude = self._as_float(message.get("latitude"))
        longitude = self._as_float(message.get("longitude"))
        if latitude is None or longitude is None:
            return False

        point = GeoPoint(
            latitude=latitude,
            longitude=longitude,
            altitude=self._as_float(message.get("altitude"), 0.0) or 0.0,
            timestamp=self._extract_stamp(message.get("header", {}).get("stamp")),
            source=self.AIRCRAFT_TOPIC,
        )
        sample = FlightSample(
            point=point,
            covariance=[float(value) for value in message.get("position_covariance", [])],
            fix_type=str(message.get("position_covariance_type", "")),
        )
        self.state.update_aircraft(sample)
        self.logger.log_aircraft(
            latitude=point.latitude,
            longitude=point.longitude,
            altitude=point.altitude,
            fix_type=sample.fix_type,
            timestamp=point.timestamp,
        )
        return True

    def _handle_target(self, message: Dict[str, Any]) -> bool:
        position = message.get("position", {})
        latitude = self._as_float(position.get("latitude"))
        longitude = self._as_float(position.get("longitude"))
        if latitude is None or longitude is None:
            return False

        point = GeoPoint(
            latitude=latitude,
            longitude=longitude,
            altitude=self._as_float(position.get("altitude"), 0.0) or 0.0,
            timestamp=self._extract_stamp(position.get("header", {}).get("stamp")),
            source=self.TARGET_TOPIC,
        )
        tracker_id = int(message.get("tracker_id", 0))
        vehicle_name = str(message.get("vehicle_name", "unknown"))
        label = str(message.get("label", ""))
        key = self._target_key(tracker_id, label, vehicle_name)
        target = TargetRecord(
            tracker_id=tracker_id,
            vehicle_name=vehicle_name,
            key=key,
            label=label,
            position=point,
        )
        self.state.update_target(target)
        self.logger.log_target(
            vehicle_name=vehicle_name,
            tracker_id=tracker_id,
            latitude=point.latitude,
            longitude=point.longitude,
            altitude=point.altitude,
            timestamp=point.timestamp,
        )
        return True

    def _target_key(self, tracker_id: int, label: str, vehicle_name: str) -> str:
        label_key = label.strip().lower().replace(" ", "_")
        vehicle_key = vehicle_name.strip().lower().replace(" ", "_")
        suffix = label_key or vehicle_key or "unknown"
        return f"{tracker_id}:{suffix}"

    def _as_float(self, value: Any, default: Optional[float] = None) -> Optional[float]:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _extract_stamp(self, stamp: Dict[str, Any] | None) -> Optional[datetime]:
        if not stamp:
            return None
        sec = int(stamp.get("sec", 0))
        nanosec = int(stamp.get("nanosec", 0))
        total_seconds = sec + (nanosec / 1_000_000_000.0)
        return datetime.fromtimestamp(total_seconds, tz=timezone.utc)
