from typing import Any

from .validations import ValidationException
from .const import (
    UNIQUE_ID_KEY,
    DEVICE_VALIDATION_UNIQUE_ID_INVALID_ERROR
)


class DeviceValidation:

    @staticmethod
    def validate_device_unique_id(data: dict[str, Any]) -> None:
        unique_id = data.get(UNIQUE_ID_KEY)

        if not unique_id or len(unique_id) < 21:
            raise ValidationException(
                DEVICE_VALIDATION_UNIQUE_ID_INVALID_ERROR)

    @staticmethod
    def validate_device(data: dict[str, Any]) -> None:
        data = DeviceValidation.validate_device_unique_id(data)
