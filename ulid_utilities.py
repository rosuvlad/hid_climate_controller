import hashlib
import base64


class UlidUtilities:
    """Class for UlidUtilities."""

    @staticmethod
    def encode_string_as_ulid(input_string: str) -> str:
        # Generate a SHA256 hash of the string
        hash_result = hashlib.sha256(input_string.encode()).digest()

        # Convert the hash to a base64 encoding and remove any padding characters
        encoded = base64.b64encode(hash_result).decode().rstrip("=")

        # Return the first 26 characters
        return encoded[:26]
