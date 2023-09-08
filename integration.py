from __future__ import annotations

import logging

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr

from .concurrent_dict import ConcurrentDict
from .climate_service import ClimateService
from .climate_commands import ClimateCommands
from .climate_bridge import ClimateBridge
from .const import (
    DOMAIN,
    ENTITY_ID_KEY,
    FRIENDLY_NAME_KEY,
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
        _LOGGER.debug("Running async_setup_entry for config entry data: %s", entry.data)

        device_deferred_registration = entry.data.get(CONTROLLER_KEY, {}).get(
            DEVICE_DEFERRED_REGISTRATION_KEY, True
        )

        if device_deferred_registration:
            return True

        await self._async_register_device(entry)

        return True

    async def async_unload_entry(self, entry: ConfigEntry) -> bool:
        _LOGGER.debug(
            "Running async_unload_entry for config entry data: %s", entry.data
        )

        device_deferred_registration = entry.data.get(CONTROLLER_KEY, {}).get(
            DEVICE_DEFERRED_REGISTRATION_KEY, True
        )

        if device_deferred_registration:
            return True

        await self._async_unregister_device(entry)

        return True

    async def _async_register_device(self, entry: ConfigEntry) -> None:
        _LOGGER.debug("Running async_register_device for config entry: %s", entry)

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
                self._hass,
                self._climate_commands,
                self._async_climate_bridge_removal_requested,
                climate_config,
            ),
        )

        return await climate_bridge.register_controller(controller_config)

    async def _async_unregister_device(self, entry: ConfigEntry) -> None:
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

        climate_bridge = self._climate_bridges.get(climate_entity_id)
        if not climate_bridge:
            return

        await climate_bridge.unregister_controller(controller_config)

    async def _async_climate_bridge_removal_requested(self, entity_id: str) -> None:
        if not entity_id:
            return

        _LOGGER.debug(
            "Removing climate bridge %s - Action was requested because of childless climate bridge",
            entity_id,
        )
        climate_bridge = self._climate_bridges.pop(entity_id)
        if not climate_bridge:
            return

        await climate_bridge.destroy()
