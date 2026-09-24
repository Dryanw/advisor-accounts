import threading
import time


class IdempotencyCache:
    def __init__(self, ttl_seconds: int = 86400):
        self._store: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def get(self, key: str) -> dict | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() > entry["expires_at"]:
                del self._store[key]
                return None
            return entry

    def set_if_absent(self, key: str) -> bool:
        """Reserve the key. Returns True if this call claimed it,
        False if another request already holds it (in-flight or done)."""
        with self._lock:
            entry = self._store.get(key)
            if entry is not None and time.monotonic() <= entry["expires_at"]:
                return False
            self._store[key] = {"result": None, "expires_at": time.monotonic() + self._ttl}
            return True

    def complete(self, key: str, result: dict) -> None:
        with self._lock:
            if key in self._store:
                self._store[key]["result"] = result

    def release(self, key: str) -> None:
        # Call on failure, so a legitimately-failed attempt can be retried
        # rather than permanently stuck as "reserved."
        with self._lock:
            self._store.pop(key, None)


idempotency_cache = IdempotencyCache()
