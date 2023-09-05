from __future__ import annotations

import logging
import json

from typing import Any
from voluptuous.error import Error

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr
from homeassistant.loader import async_get_integration
from homeassistant.components import mqtt

from .validators import validate_discovery_info
from .concurrent_dict import ConcurrentDict
from .climate_service import ClimateService
from .climate_commands import ClimateCommands
from .climate_bridge import ClimateBridge
from .const import (
    DOMAIN,
    ENTITY_ID_KEY,
    FRIENDLY_NAME_KEY,
    DEVICE_UNIQUE_ID_KEY,
    DEVICE_NAME_KEY,
    DEVICE_KEY,
    DEVICE_MODEL_KEY,
    DEVICE_MANUFACTURER_KEY,
    DEVICE_SW_VERSION_KEY,
    DEVICE_HW_VERSION_KEY,
    DEVICE_DEFERRED_REGISTRATION_KEY,
    CONTROLLER_KEY,
    CLIMATE_KEY,
)

_LOGGER = logging.getLogger(__name__)


class HIDClimateControllerIntegration:
    _instance = None

    _initialized = False
    _hass = None
    _device_discovery_topic = None
    _pending_device_registrations = ConcurrentDict()
    _climate_service = None
    _climate_commands = None
    _climate_bridges = ConcurrentDict()

    @staticmethod
    def get_instance():
        if HIDClimateControllerIntegration._instance is None:
            HIDClimateControllerIntegration()
        return HIDClimateControllerIntegration._instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HIDClimateControllerIntegration, cls).__new__(cls)

        return cls._instance

    async def init(self, hass: HomeAssistant) -> None:
        if self._initialized:
            return

        self._hass = hass
        self._climate_service = ClimateService(self._hass)
        self._climate_commands = ClimateCommands(self._climate_service)
        self._hass.data.setdefault(DOMAIN, self)
        self._initialized = True

    async def async_setup_entry(self, entry: ConfigEntry) -> bool:
        await self.async_register_device_or_defer(entry)

        return True

    async def async_unload_entry(self, entry: ConfigEntry) -> bool:
        controller_config = entry.data.get(CONTROLLER_KEY, {})
        climate_config = entry.data.get(CLIMATE_KEY, {})
        if len(controller_config) == 0 or len(climate_config) == 0:
            return

        unique_id = controller_config.get(ENTITY_ID_KEY)
        if not unique_id:
            return

        climate_entity_id = climate_config.get(ENTITY_ID_KEY)
        if not climate_entity_id:
            return

        await self._async_stop_deferred_device_registration_if_pending(unique_id)

        climate_bridge = self._climate_bridges.get(climate_entity_id)
        if not climate_bridge:
            return

        await climate_bridge.unregister_controller(controller_config)

        return True

    async def async_register_device_or_defer(self, entry: ConfigEntry) -> None:
        if entry.data.get(CONTROLLER_KEY, {}).get(
            DEVICE_DEFERRED_REGISTRATION_KEY, True
        ):
            await self._async_start_deferred_device_registration(entry)
        else:
            await self._async_register_device(entry)

    async def _async_register_device(self, entry: ConfigEntry) -> None:
        controller_config = entry.data.get(CONTROLLER_KEY, {})
        climate_config = entry.data.get(CLIMATE_KEY, {})

        if len(controller_config) == 0 or len(climate_config) == 0:
            return

        climate_entity_id = climate_config.get(ENTITY_ID_KEY)
        if not climate_entity_id:
            return

        device_registry = dr.async_get(self._hass)

        device_data = controller_config.get(DEVICE_KEY, {})

        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, controller_config.get(ENTITY_ID_KEY))},
            name=controller_config.get(FRIENDLY_NAME_KEY),
            model=device_data.get(DEVICE_MODEL_KEY),
            manufacturer=device_data.get(DEVICE_MANUFACTURER_KEY),
            sw_version=device_data.get(DEVICE_SW_VERSION_KEY),
            hw_version=device_data.get(DEVICE_HW_VERSION_KEY),
        )

        climate_bridge = self._climate_bridges.setdefault_with_func_construct(
            climate_entity_id,
            lambda: ClimateBridge(
                self._hass, mqtt, self._climate_commands, climate_config
            ),
        )

        return await climate_bridge.register_controller(controller_config)

    async def _async_start_deferred_device_registration(
        self, entry: ConfigEntry
    ) -> None:
        controller_data = entry.data.get(CONTROLLER_KEY, {})

        unique_id = controller_data.get(ENTITY_ID_KEY)
        if not unique_id:
            return

        device_discovery_topic = await self._async_get_device_discovery_topic()
        device_discovery_topic = device_discovery_topic.replace(
            "/+/", f"/{unique_id}/", 1
        )

        unsubscribe_callback = await mqtt.async_subscribe(
            self._hass,
            device_discovery_topic,
            self._async_handle_deferred_device_registration_message,
        )

        self._pending_device_registrations[unique_id] = {
            "entry": entry,
            "unsubscribe": unsubscribe_callback,
        }

    async def _async_stop_deferred_device_registration_if_pending(
        self, unique_id: str
    ) -> None:
        if not unique_id:
            return

        if unique_id in self._pending_device_registrations:
            pending_device_registration = self._pending_device_registrations.pop(
                unique_id
            )
            if pending_device_registration:
                unsubscribe_callback = pending_device_registration.get("unsubscribe")
                if unsubscribe_callback:
                    unsubscribe_callback()

    async def _async_handle_deferred_device_registration_message(self, msg) -> None:
        unique_id = self._get_second_last_segment(msg.topic, "/")
        if not unique_id:
            return

        errors = {}

        try:
            discovery_info = json.loads(msg.payload) or {}

            errors = validate_discovery_info(discovery_info)
            if len(errors) > 0:
                raise Error

            discovery_info_unique_id = discovery_info.get(DEVICE_UNIQUE_ID_KEY)
            if unique_id != discovery_info_unique_id:
                await self._async_stop_deferred_device_registration_if_pending(
                    unique_id
                )
                return

            entry = self._pending_device_registrations.get(unique_id, {}).get("entry")
            if not entry:
                await self._async_stop_deferred_device_registration_if_pending(
                    unique_id
                )
                return

            data = {**entry.data}
            data[CONTROLLER_KEY] = {
                ENTITY_ID_KEY: unique_id,
                FRIENDLY_NAME_KEY: discovery_info.get(DEVICE_NAME_KEY) or unique_id,
                DEVICE_KEY: discovery_info.get(DEVICE_KEY, {}),
                DEVICE_DEFERRED_REGISTRATION_KEY: False,
            }

            updated = self._hass.config_entries.async_update_entry(entry, data=data)
            if updated:
                await self._async_stop_deferred_device_registration_if_pending(
                    unique_id
                )
                entry = self._hass.config_entries.async_get_entry(entry.entry_id)
                await self._async_register_device(entry)
        except Exception as ex:  # pylint: disable=broad-except
            await self._async_stop_deferred_device_registration_if_pending(unique_id)
            raise ex

    def _get_second_last_segment(
        self, input_str: str, delimiter: str = "/", default: str = None
    ) -> str:
        if input_str is None:
            return default
        try:
            return input_str.split(delimiter)[-2]
        except IndexError:
            return default

    async def _async_get_device_discovery_topic(self) -> str | None:
        try:
            if not self._device_discovery_topic:
                integration = await async_get_integration(self._hass, DOMAIN)
                topics = integration.manifest.get("mqtt", [])
                if len(topics) == 0:
                    return None
                self._device_discovery_topic = topics[0]
            return self._device_discovery_topic
        except Exception:  # pylint: disable=broad-except
            return None
