from __future__ import annotations

import logging
import asyncio

from typing import Any

from homeassistant.core import HomeAssistant, Context, Event, State
from homeassistant.const import EVENT_STATE_CHANGED

from .concurrent_dict import ConcurrentDict
from .climate_commands import ClimateCommands
from .device_controller import DeviceController
from .const import TRIGGERING_ENTITY_ULID_KEY, TRIGGERING_ENTITY_ID_KEY, ENTITY_ID_KEY

_LOGGER = logging.getLogger(__name__)


class ClimateBridge:
    _hass = None
    _config = None
    _entity_id = None
    _previous_event = None
    _climate_commands = None
    _climate_destroy_callback = None
    _controllers = None
    _unsubscribe = None

    def __init__(
        self,
        hass: HomeAssistant,
        climate_commands: ClimateCommands,
        climate_destroy_callback: function,
        config: dict[str, Any],
    ) -> None:
        self._hass = hass
        self._config = config
        self._entity_id = self._config.get(ENTITY_ID_KEY)

        self._climate_commands = climate_commands
        self._climate_destroy_callback = climate_destroy_callback
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

    async def register_controller(self, config: dict[str, Any]) -> DeviceController:
        entity_id = config.get(ENTITY_ID_KEY)
        if not entity_id:
            _LOGGER.debug(
                "Missing entity_id in config. Skipping device controller registration"
            )
            return

        async def build_controller() -> DeviceController:
            device_controller = DeviceController(self._hass, config)
            await device_controller.initialize()
            return device_controller

        device_controller = (
            await self._controllers.async_setdefault_with_func_construct(
                entity_id, build_controller
            )
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
            state = self._get_mutated_state_from_event(self._previous_event)
            await device_controller.state_changed(state)

        return device_controller

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

        await self._request_removal_if_childless()

    async def destroy(self) -> None:
        _LOGGER.debug("Destroying climate bridge %s", self._entity_id)

        _LOGGER.debug("Unsubscribing from state changed events")
        if self._unsubscribe:
            self._unsubscribe()

        keys = self._controllers.keys()
        if len(keys) == 0:
            _LOGGER.debug("Unregistering all device controllers and destroying them")
            for key in keys:
                controller = self._controllers.pop(key)
                if controller:
                    await controller.destroy()

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

        state = self._get_mutated_state_from_event(current_event)

        _LOGGER.debug(
            "Climate bridge %s is handling state changed event from climate entity %s",
            self._entity_id,
            entity_id,
        )

        async def local_handle_event(
            controller: DeviceController, state: dict[str, Any]
        ):
            await controller.state_changed(state)

        tasks = [
            local_handle_event(controller, state)
            for controller in self._controllers.values()
        ]

        await asyncio.gather(*tasks)

        self._previous_event = current_event

    async def _request_removal_if_childless(self) -> None:
        if self._climate_destroy_callback and len(self._controllers) == 0:
            await self._climate_destroy_callback(self._entity_id)

    def _get_mutated_state_from_event(self, event: Event) -> dict[str, Any]:
        triggering_entity_ulid = str(event.context.parent_id)

        event_state = event.data.get("new_state")
        state = event_state.as_compressed_state() if event_state else {}

        triggering_entity_ulid = state.get("context", {}).get("parent_id")
        state[TRIGGERING_ENTITY_ULID_KEY] = triggering_entity_ulid

        triggering_entity_id = next(
            (
                key
                for key, value in self._controllers.items()
                if value.matches(triggering_entity_ulid)
            ),
            None,
        )
        state[TRIGGERING_ENTITY_ID_KEY] = triggering_entity_id

        return state
