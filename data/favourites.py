import json
from pathlib import Path

_CONFIG = Path.home() / ".config" / "radiox"
_FAV_FILE = _CONFIG / "favourites.json"
_RECENT_FILE = _CONFIG / "recent.json"


class FavouritesManager:
    def __init__(self):
        _CONFIG.mkdir(parents=True, exist_ok=True)
        self._uuids: set[str] = set(self._load(_FAV_FILE))

    def is_favourite(self, uuid: str) -> bool:
        return uuid in self._uuids

    def set(self, uuid: str, is_fav: bool):
        if is_fav:
            self._uuids.add(uuid)
        else:
            self._uuids.discard(uuid)
        self._save(_FAV_FILE, list(self._uuids))

    def uuids(self) -> set[str]:
        return set(self._uuids)

    @staticmethod
    def _load(path: Path) -> list:
        try:
            return json.loads(path.read_text())
        except Exception:
            return []

    @staticmethod
    def _save(path: Path, data: list):
        try:
            path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"radiox: failed to save {path}: {e}", flush=True)


class RecentManager:
    MAX = 20

    def __init__(self):
        _CONFIG.mkdir(parents=True, exist_ok=True)
        self._uuids: list[str] = self._load()

    def add(self, uuid: str):
        try:
            self._uuids.remove(uuid)
        except ValueError:
            pass
        self._uuids.insert(0, uuid)
        self._uuids = self._uuids[: self.MAX]
        self._save()

    def uuids(self) -> list[str]:
        return list(self._uuids)

    def clear(self):
        self._uuids = []
        self._save()

    def _load(self) -> list:
        try:
            return json.loads(_RECENT_FILE.read_text())
        except Exception:
            return []

    def _save(self):
        try:
            _RECENT_FILE.write_text(json.dumps(self._uuids, indent=2))
        except Exception as e:
            print(f"radiox: failed to save recent: {e}", flush=True)
