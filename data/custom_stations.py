from __future__ import annotations
import json
import uuid
from pathlib import Path

_CONFIG = Path.home() / ".config" / "dyedfox-radio"
_CUSTOM_FILE = _CONFIG / "custom_stations.json"


class CustomStationsManager:
    def __init__(self):
        _CONFIG.mkdir(parents=True, exist_ok=True)
        self._stations: list[dict] = self._load()

    def all(self) -> list[dict]:
        return list(self._stations)

    def add(self, name: str, url: str, favicon: str = "") -> dict:
        station = {
            "stationuuid": f"custom-{uuid.uuid4()}",
            "name": name,
            "url_resolved": url,
            "favicon": favicon,
            "custom": True,
            "tags": "",
            "country": "",
            "language": "",
            "codec": "",
            "bitrate": 0,
            "votes": 0,
        }
        self._stations.insert(0, station)
        self._save()
        return station

    def update(self, station_uuid: str, name: str, url: str, favicon: str):
        for s in self._stations:
            if s.get("stationuuid") == station_uuid:
                s["name"] = name
                s["url_resolved"] = url
                s["favicon"] = favicon
                break
        self._save()

    def remove(self, station_uuid: str):
        self._stations = [s for s in self._stations if s.get("stationuuid") != station_uuid]
        self._save()

    def _load(self) -> list:
        try:
            return json.loads(_CUSTOM_FILE.read_text())
        except Exception:
            return []

    def _save(self):
        try:
            _CUSTOM_FILE.write_text(json.dumps(self._stations, indent=2))
        except Exception as e:
            print(f"dyedfox-radio: failed to save custom stations: {e}", flush=True)
