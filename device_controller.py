from __future__ import annotations

import logging

from typing import Any

from homeassistant.core import HomeAssistant

from .const import ENTITY_ID_KEY

_LOGGER = logging.getLogger(__name__)


class DeviceController:
    _hass = None
    _mqtt = None
    _config = None
    _entity_id = None

    def __init__(self, hass: HomeAssistant, mqtt: Any, config: dict[str, Any]) -> None:
        self._hass = hass
        self._mqtt = mqtt
        self._config = config
        self._entity_id = self._config.get(ENTITY_ID_KEY)

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None
