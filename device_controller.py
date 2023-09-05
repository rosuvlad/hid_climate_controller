from __future__ import annotations

import logging

from typing import Any

from homeassistant.core import HomeAssistant, Event

from .utilities import Utilities, async_throttle
from .const import ENTITY_ID_KEY

_LOGGER = logging.getLogger(__name__)


class DeviceController:
    _hass = None
    _mqtt = None
    _config = None
    _entity_id = None
    _entity_id_ulid = None
    _previous_state = None

    def __init__(self, hass: HomeAssistant, mqtt: Any, config: dict[str, Any]) -> None:
        self._hass = hass
        self._mqtt = mqtt
        self._config = config
        self._entity_id = self._config.get(ENTITY_ID_KEY)
        self._entity_id_ulid = Utilities.encode_string_as_ulid(self._entity_id)

    async def state_changed(self, event: Event | None) -> None:
        if not event or not event.context:
            _LOGGER.debug("Malformed event received. Skipping event handling")
            return

        parent_id = event.context.parent_id
        new_state = event.data.get("new_state")
        if not new_state:
            _LOGGER.debug("Malformed event received. Skipping event handling")
            return

        await self._async_handle_new_state(parent_id, new_state)

    async def destroy(self) -> None:
        return None

    @async_throttle(250)
    async def _async_handle_new_state(
        self, parent_id: str | None, state: dict[str, Any]
    ) -> None:
        _LOGGER.debug(
            "Device controller %s (%s) is handling state changed event triggered by %s with data: %s",
            self._entity_id,
            self._entity_id_ulid,
            parent_id,
            state,
        )
