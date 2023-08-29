import voluptuous as vol

from typing import Any
from voluptuous.error import Invalid, MultipleInvalid
from homeassistant.helpers import config_validation as cv

from .const import (
    REQUIRED_INPUT_ERROR,
    DEVICE_UNIQUE_ID_REGEX,
    DEVICE_SW_VERSION_REGEX,
    DEVICE_UNIQUE_ID_KEY,
    DEVICE_NAME_KEY,
    DEVICE_KEY,
    DEVICE_MODEL_KEY,
    DEVICE_MANUFACTURER_KEY,
    DEVICE_SW_VERSION_KEY,
    CONTROLLER_ENTITY_ID_KEY,
    CONTROLLER_NAME_KEY,
    CLIMATE_ENTITY_ID_KEY,
)

DISCOVERY_INFO_SCHEMA = vol.Schema(
    {
        vol.Required(
            DEVICE_UNIQUE_ID_KEY, msg=REQUIRED_INPUT_ERROR, default=""
        ): vol.All(cv.string, vol.Match(DEVICE_UNIQUE_ID_REGEX)),
        vol.Optional(DEVICE_NAME_KEY, default=""): cv.string,
        vol.Optional(DEVICE_KEY): {
            vol.Optional(DEVICE_MODEL_KEY, default=""): cv.string,
            vol.Optional(DEVICE_MANUFACTURER_KEY, default=""): cv.string,
            vol.Optional(DEVICE_SW_VERSION_KEY, default=""): vol.All(
                cv.string, vol.Match(DEVICE_SW_VERSION_REGEX)
            ),
        },
    },
    extra=vol.ALLOW_EXTRA,
)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONTROLLER_ENTITY_ID_KEY, msg=REQUIRED_INPUT_ERROR, default=""
        ): vol.All(cv.string, vol.Match(DEVICE_UNIQUE_ID_REGEX)),
        vol.Optional(CONTROLLER_NAME_KEY, default=""): cv.string,
        vol.Required(
            CLIMATE_ENTITY_ID_KEY, msg=REQUIRED_INPUT_ERROR, default=""
        ): cv.string,
    }
)


def validate_discovery_info(data: dict[str, Any]) -> dict[str, Invalid]:
    errors = {}
    try:
        DISCOVERY_INFO_SCHEMA(data)
    except MultipleInvalid as ex:
        for error in ex.errors:
            path = ".".join(map(str, error.path))
            errors[path] = f"{path}: {error.msg.capitalize()}"
    except Invalid as ex:
        path = ".".join(map(str, error.path))
        errors[path] = f"{path}: {error.msg.capitalize()}"
    return errors


def validate_config(data: dict[str, Any]) -> dict[str, Invalid]:
    errors = {}
    try:
        CONFIG_SCHEMA(data)
    except MultipleInvalid as ex:
        for error in ex.errors:
            path = ".".join(map(str, error.path))
            errors[path] = error.msg.capitalize()
    except Invalid as ex:
        path = ".".join(map(str, error.path))
        errors[path] = error.msg.capitalize()
    return errors
