from __future__ import annotations

import logging

from typing import Any

from homeassistant.core import HomeAssistant, Event

from .const import ENTITY_ID_KEY

_LOGGER = logging.getLogger(__name__)


class DeviceController:
    _hass = None
    _mqtt = None
    _config = None
    _entity_id = None
    _previous_state = None

    def __init__(self, hass: HomeAssistant, mqtt: Any, config: dict[str, Any]) -> None:
        self._hass = hass
        self._mqtt = mqtt
        self._config = config
        self._entity_id = self._config.get(ENTITY_ID_KEY)

    def should_handle(self, entity_id) -> Any:
        """Check if the device controller can handle the given entity_id."""
        handle = self._entity_id != entity_id
        _LOGGER.debug(
            "Checking if device controller can handle entity_id %s: %s",
            entity_id,
            handle,
        )
        return handle

    async def state_changed(self, event: Event) -> None:
        """Handle state changes for the given entity_id."""
        _LOGGER.info(
            "State changed for entity_id %s with context: %s", entity_id, event.context
        )

        entity_id = event.context.parent_id
        if self.should_handle(entity_id):
            return

        _LOGGER.info(
            "Device controller: %s handling state changed for entity_id %s", entity_id
        )

    async def destroy(self) -> None:
        return None
