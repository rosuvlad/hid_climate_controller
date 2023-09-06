import threading


class ConcurrentDict:
    def __init__(self) -> None:
        self._dict = {}
        self._lock = threading.Lock()

    def __iter__(self):
        with self._lock:
            return iter(self._dict.keys())

    def __len__(self):
        with self._lock:
            return len(self._dict)

    def __setitem__(self, key, value):
        self.set(key, value)

    def __getitem__(self, key):
        return self.get(key)

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

    def setdefault_with_func_construct(self, key, func=None):
        with self._lock:
            if key in self._dict:
                return self._dict[key]
            else:
                self._dict[key] = func() if func is not None else None
                return self._dict[key]

    def pop(self, key, default=None):
        with self._lock:
            return self._dict.pop(key, default)

    def remove(self, key):
        with self._lock:
            if key in self._dict:
                del self._dict[key]

    async def async_try_remove_and_execute_action(
        self, key, action_func, condition_func=None
    ):
        with self._lock:
            value = self._dict.pop(key, None)
            if value is None:
                return
            should_execute = True
            if condition_func:
                try:
                    should_execute = await condition_func(self._dict, value)
                except Exception:  # pylint: disable=broad-except
                    should_execute = False
                if not should_execute:
                    return
            try:
                await action_func(self._dict, value)
            except Exception:  # pylint: disable=broad-except
                return

    def keys(self):
        with self._lock:
            return list(self._dict.keys())

    def values(self):
        with self._lock:
            return list(self._dict.values())
