from __future__ import annotations

import logging

from typing import Any

from homeassistant.core import HomeAssistant

from .concurrent_dict import ConcurrentDict
from .device_controller import DeviceController
from .const import ENTITY_ID_KEY

_LOGGER = logging.getLogger(__name__)


class ClimateBridge:
    _hass = None
    _mqtt = None
    _config = None
    _entity_id = None
    _controllers = ConcurrentDict()

    def __init__(self, hass: HomeAssistant, mqtt: Any, config: dict[str, Any]) -> None:
        self._hass = hass
        self._mqtt = mqtt
        self._config = config
        self._entity_id = self._config.get(ENTITY_ID_KEY)

    def can_handle(self, entity_id) -> Any:
        return self._entity_id == entity_id

    async def state_changed(self, entity_id: str, event: Any) -> None:
        _LOGGER.info("State changed %s: %s", entity_id, event.context)

    async def register_controller(self, config: dict[str, Any]) -> None:
        _LOGGER.info("Registering controller %s", config)

        entity_id = config.get(ENTITY_ID_KEY)
        if not entity_id:
            return

        device_controller = self._controllers.setdefault(
            entity_id, DeviceController(self._hass, self._mqtt, config)
        )
        if device_controller:
            await device_controller.connect()

    async def unregister_controller(self, config: dict[str, Any]) -> None:
        _LOGGER.info("Unregistering controller %s", config)

        entity_id = config.get(ENTITY_ID_KEY)
        if not entity_id:
            return

        device_controller = self._controllers.pop(entity_id, None)
        if device_controller:
            await device_controller.disconnect()
