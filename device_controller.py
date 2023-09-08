from __future__ import annotations

import logging

from typing import Any

from homeassistant.core import HomeAssistant, Event, State
from homeassistant.components import mqtt

from .utilities import Utilities, async_throttle
from .const import (
    STATE_TOPIC,
    COMMAND_TOPIC,
    TRIGGERING_ENTITY_ULID_KEY,
    TRIGGERING_ENTITY_ID_KEY,
    ENTITY_ID_KEY,
)

_LOGGER = logging.getLogger(__name__)


class DeviceController:
    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        self._hass = hass
        self._config = config
        self._entity_id = self._config.get(ENTITY_ID_KEY)
        self._entity_id_ulid = Utilities.encode_string_as_ulid(self._entity_id)
        self._state_topic = STATE_TOPIC.format(unique_id=self._entity_id)
        self._command_topic = COMMAND_TOPIC.format(unique_id=self._entity_id)

    async def initialize(self) -> None:
        _LOGGER.info(
            "Initializing device controller %s (%s)",
            self._entity_id,
            self._entity_id_ulid,
        )

    def matches(self, ulid: str) -> bool:
        return ulid == self._entity_id_ulid

    async def state_changed(self, state: dict[str, Any]) -> None:
        triggering_entity_id = state.get(TRIGGERING_ENTITY_ID_KEY)

        _LOGGER.info(
            "Device controller %s (%s) is handling state changed event triggered by %s with data: %s",
            self._entity_id,
            self._entity_id_ulid,
            triggering_entity_id,
            state,
        )

    async def destroy(self) -> None:
        return None
