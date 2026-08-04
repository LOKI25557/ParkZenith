import time
import threading
from typing import Dict, Any, Optional

class SimpleCache:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() < entry["expires_at"]:
                    return entry["value"]
                else:
                    del self._cache[key]
            return None

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl_seconds
            }

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

cache = SimpleCache()
