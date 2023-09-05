from __future__ import annotations

import logging

from typing import Any
from voluptuous.error import Error

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class ClimateBridge:
    _hass = None
    _mqtt = None
    _climate_config = None

    def __init__(
        self, hass: HomeAssistant, mqtt: Any, climate_config: dict[str, Any]
    ) -> None:
        self._hass = hass
        self._mqtt = mqtt
        self._climate_config = climate_config

    async def register_controller(self, controller_config: dict[str, Any]) -> None:
        _LOGGER.info("Registering controller %s", controller_config)

    async def unregister_controller(self, controller_config: dict[str, Any]) -> None:
        _LOGGER.info("Unregistering controller %s", controller_config)
