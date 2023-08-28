import voluptuous as vol

from typing import Any
from .validations import ValidationException
from .const import UNIQUE_ID_KEY, DEVICE_VALIDATION_UNIQUE_ID_INVALID_ERROR


class DeviceValidation:
    @staticmethod
    def validate_device_unique_id(val: str) -> str:
        if val is None or len(val) < 21:
            raise vol.Invalid(DEVICE_VALIDATION_UNIQUE_ID_INVALID_ERROR)

    @staticmethod
    def validate_device(data: dict[str, Any]) -> dict[str, Any]:
        DeviceValidation.validate_device_unique_id(data.get(UNIQUE_ID_KEY))
