from __future__ import annotations

import logging

from typing import Any
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .integration import HIDClimateControllerIntegration
from .const import DOMAIN


_logger = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    await HIDClimateControllerIntegration.get_instance().init(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await HIDClimateControllerIntegration.get_instance().async_setup_entry(entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await HIDClimateControllerIntegration.get_instance().async_unload_entry(
        entry
    )
