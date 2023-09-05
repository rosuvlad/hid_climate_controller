import hashlib
import base64
import functools
import time


class Utilities:
    """Class for UlidUtilities."""

    @staticmethod
    def encode_string_as_ulid(input_string: str) -> str:
        # Generate a SHA256 hash of the string
        hash_result = hashlib.sha256(input_string.encode()).digest()

        # Convert the hash to a base64 encoding and remove any padding characters
        encoded = base64.b64encode(hash_result).decode().rstrip("=")

        # Return the first 26 characters
        return encoded[:26]


def throttle(milliseconds):
    """Throttle function call if called with same args within the specified timeout."""

    def decorator(fn):
        cache = {}

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, frozenset(kwargs.items()))
            current_time = time.time() * 1000  # convert to milliseconds

            if key in cache and current_time - cache[key] < milliseconds:
                print(f"Throttled: {fn.__name__}({args}, {kwargs})")
                return None

            cache[key] = current_time
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def async_throttle(ms):
    def decorator(fn):
        last_called = {}

        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            now = time.time()
            key = (args, frozenset(kwargs.items()))

            if key in last_called and now - last_called[key] < ms / 1000:
                return

            last_called[key] = now
            return await fn(*args, **kwargs)

        return wrapper

    return decorator
