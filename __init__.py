from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info(
        "Setting up config entry: %s with data: %s", entry.unique_id, entry.data
    )

    hass.data.setdefault(DOMAIN, {})
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info("Removing config entry: %s with data: %s", entry.unique_id, entry.data)

    if entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(entry.entry_id)

    return True
