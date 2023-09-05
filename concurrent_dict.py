import threading


class ConcurrentDict:
    def __init__(self) -> None:
        self._dict = {}
        self._lock = threading.Lock()

    def __iter__(self):
        with self._lock:
            return iter(self._dict.keys())

    def set(self, key, value):
        with self._lock:
            self._dict[key] = value

    def get(self, key, default=None):
        with self._lock:
            return self._dict.get(key, default)

    def setdefault(self, key, default=None):
        with self._lock:
            if key in self._dict:
                return self._dict[key]
            else:
                self._dict[key] = default
                return default

    def pop(self, key, default=None):
        with self._lock:
            return self._dict.pop(key, default)

    def remove(self, key):
        with self._lock:
            if key in self._dict:
                del self._dict[key]

    def keys(self):
        with self._lock:
            return list(self._dict.keys())

    def values(self):
        with self._lock:
            return list(self._dict.values())
