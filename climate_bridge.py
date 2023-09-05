from __future__ import annotations

import logging
import asyncio

from typing import Any

from homeassistant.core import HomeAssistant, Context, Event
from homeassistant.const import EVENT_STATE_CHANGED

from .ulid_utilities import UlidUtilities
from .concurrent_dict import ConcurrentDict
from .device_controller import DeviceController
from .const import ENTITY_ID_KEY

_LOGGER = logging.getLogger(__name__)


class ClimateBridge:
    """Represents a bridge for climate devices in the Home Assistant context."""

    _hass = None
    _mqtt = None
    _config = None
    _entity_id = None
    _previous_event = None
    _unsubscribe = None

    _controllers = ConcurrentDict()

    def __init__(self, hass: HomeAssistant, mqtt: Any, config: dict[str, Any]) -> None:
        self._hass = hass
        self._mqtt = mqtt
        self._config = config
        self._entity_id = self._config.get(ENTITY_ID_KEY)
        self._unsubscribe = self._hass.bus.async_listen(
            EVENT_STATE_CHANGED, self._async_handle_state_changed
        )

    async def register_controller(self, config: dict[str, Any]) -> None:
        entity_id = config.get(ENTITY_ID_KEY)
        if not entity_id:
            return

        device_controller = self._controllers.setdefault(
            entity_id, DeviceController(self._hass, self._mqtt, config)
        )
        if device_controller:
            await device_controller.state_changed(self._previous_event)

    async def unregister_controller(self, config: dict[str, Any]) -> None:
        entity_id = config.get(ENTITY_ID_KEY)
        if not entity_id:
            return

        device_controller = self._controllers.pop(entity_id, None)
        if device_controller:
            await device_controller.destroy()

    async def destroy(self) -> None:
        if self._unsubscribe:
            self._unsubscribe()

    def _should_handle(self, entity_id) -> Any:
        return self._entity_id == entity_id

    async def _async_handle_state_changed(self, event: Event):
        entity_id = event.data.get("entity_id")
        if not entity_id or not self._should_handle(entity_id):
            return

        current_event = event

        async def local_handle_event(controller: DeviceController, event: Event):
            await controller.state_changed(event)

        tasks = [
            local_handle_event(controller, current_event)
            for controller in self._controllers.values()
        ]

        await asyncio.gather(*tasks)

        self._previous_event = current_event
