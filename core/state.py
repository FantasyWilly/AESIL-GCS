

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Dict, List, Optional


@dataclass(slots=True)
class GeoPoint:
    latitude: float
    longitude: float
    altitude: float = 0.0
    timestamp: Optional[datetime] = None
    source: str = ""


@dataclass(slots=True)
class FlightSample:
    point: GeoPoint
    covariance: List[float] = field(default_factory=list)
    fix_type: str = ""


@dataclass(slots=True)
class TargetRecord:
    tracker_id: int
    vehicle_name: str
    key: str
    position: GeoPoint
    label: str = ""


@dataclass(slots=True)
class AppState:
    aircraft: Optional[FlightSample] = None
    aircraft_track: List[FlightSample] = field(default_factory=list)
    targets: Dict[str, TargetRecord] = field(default_factory=dict)
    target_history: List[TargetRecord] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def update_aircraft(self, sample: FlightSample) -> None:
        with self._lock:
            self.aircraft = sample
            self.aircraft_track.append(sample)

    def update_target(self, record: TargetRecord) -> None:
        with self._lock:
            self.targets[record.key] = record
            self.target_history.append(record)

    def snapshot_aircraft(self) -> Optional[FlightSample]:
        with self._lock:
            return self.aircraft

    def snapshot_track(self) -> List[FlightSample]:
        with self._lock:
            return list(self.aircraft_track)

    def snapshot_targets(self) -> Dict[str, TargetRecord]:
        with self._lock:
            return dict(self.targets)

    def clear(self) -> None:
        with self._lock:
            self.aircraft = None
            self.aircraft_track.clear()
            self.targets.clear()
            self.target_history.clear()
