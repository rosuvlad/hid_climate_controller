from __future__ import annotations

import logging
import asyncio

from typing import Any

from homeassistant.core import HomeAssistant, Context, Event, ServiceResponse
from homeassistant.const import EVENT_STATE_CHANGED

from .concurrent_dict import ConcurrentDict
from .climate_commands import ClimateCommands
from .device_controller import DeviceController
from .const import ENTITY_ID_KEY

_LOGGER = logging.getLogger(__name__)


class ClimateBridge:
    _hass = None
    _mqtt = None
    _config = None
    _entity_id = None
    _previous_event = None
    _climate_commands = None
    _controllers = None
    _unsubscribe = None

    def __init__(
        self,
        hass: HomeAssistant,
        mqtt: Any,
        climate_commands: ClimateCommands,
        config: dict[str, Any],
    ) -> None:
        self._hass = hass
        self._mqtt = mqtt
        self._config = config
        self._entity_id = self._config.get(ENTITY_ID_KEY)

        self._climate_commands = climate_commands
        self._controllers = ConcurrentDict()

        state = self._climate_commands.get_state(self._entity_id)
        if state:
            self._previous_event = Event(
                event_type=EVENT_STATE_CHANGED,
                data={"entity_id": self._entity_id, "new_state": state},
                context=Context,
            )

        self._unsubscribe = self._hass.bus.async_listen(
            EVENT_STATE_CHANGED, self._async_handle_state_changed
        )

    async def register_controller(self, config: dict[str, Any]) -> None:
        entity_id = config.get(ENTITY_ID_KEY)
        if not entity_id:
            _LOGGER.debug(
                "Missing entity_id in config. Skipping device controller registration"
            )
            return

        device_controller = self._controllers.setdefault_with_func_construct(
            entity_id, lambda: DeviceController(self._hass, self._mqtt, config)
        )
        _LOGGER.debug("Registered device controller: %s", entity_id)
        _LOGGER.debug(
            "Climate entity %s is being controlled by %s",
            self._entity_id,
            self._controllers.keys(),
        )
        if device_controller:
            _LOGGER.debug(
                "Triggering state changed event on %s device controller for initial data: %s",
                entity_id,
                self._previous_event,
            )
            await device_controller.state_changed(self._previous_event)

    async def unregister_controller(self, config: dict[str, Any]) -> None:
        entity_id = config.get(ENTITY_ID_KEY)
        if not entity_id:
            _LOGGER.debug(
                "Missing entity_id in config. Skipping device controller unregistration"
            )
            return

        device_controller = self._controllers.pop(entity_id)
        _LOGGER.debug("Unregistered device controller: %s", entity_id)
        _LOGGER.debug(
            "Climate entity %s is being controlled by %s devices",
            self._entity_id,
            self._controllers.keys(),
        )
        if device_controller:
            _LOGGER.debug("Destroying device controller: %s", entity_id)
            await device_controller.destroy()

    async def destroy(self) -> None:
        _LOGGER.debug("Destroying climate bridge %s", self._entity_id)
        _LOGGER.debug("Unregistering all device controllers and destroying them")
        for key in self._controllers.keys():
            controller = self._controllers.pop(key)
            if controller:
                await controller.destroy()

        _LOGGER.debug("Unsubscribing from state changed events")
        if self._unsubscribe:
            self._unsubscribe()

    def _should_handle(self, entity_id) -> Any:
        return self._entity_id == entity_id

    async def _async_handle_state_changed(self, event: Event):
        entity_id = event.data.get(ENTITY_ID_KEY)
        if not self._should_handle(entity_id):
            _LOGGER.debug(
                "Climate bridge %s should not handle state changed event from climate entity %s. Skipping event handling",
                self._entity_id,
                entity_id,
            )
            return

        current_event = event

        _LOGGER.debug(
            "Climate bridge %s is handling state changed event from climate entity %s",
            self._entity_id,
            entity_id,
        )

        async def local_handle_event(controller: DeviceController, event: Event):
            await controller.state_changed(event)

        tasks = [
            local_handle_event(controller, current_event)
            for controller in self._controllers.values()
        ]

        await asyncio.gather(*tasks)

        self._previous_event = current_event
