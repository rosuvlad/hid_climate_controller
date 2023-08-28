"""The HID Climate Controller integration."""
from __future__ import annotations

import logging
import json
import functools

from homeassistant.config_entries import ConfigEntry
from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import (
    DOMAIN,
    MQTT_DISCOVERY_FLOW_STEP
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config):
    """Initial setup."""

    _LOGGER.debug(f"Setup has started for {DOMAIN}")

    # Get the integration
    integration = await async_get_integration(hass, DOMAIN)

    # Access the manifest properties
    mqtt_topic = integration.manifest["mqtt"][0]

    # Create a partial function with hass pre-set
    callback = functools.partial(handle_mqtt_discovery_message, hass)

    # Subscribe to the MQTT discovery topic with the partial callback
    _LOGGER.debug(
        f'MQTT Discovery - subscribing to {mqtt_topic} for discovery')

    await mqtt.async_subscribe(hass, mqtt_topic, callback)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""

    _LOGGER.info("Setting up config entry: %s with data: %s",
                 entry.unique_id, entry.data)

    hass.data.setdefault(DOMAIN, {})
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    _LOGGER.info("Removing config entry: %s with data: %s",
                 entry.unique_id, entry.data)

    if entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(entry.entry_id)

    return True


def handle_mqtt_discovery_message(hass: HomeAssistant, msg):
    """Handle received MQTT discovery message."""

    payload = msg.payload

    data = None
    try:
        data = json.loads(payload)
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception(
            "An deserialization exception encountered while processing MQTT discovery message payload, payload: %s", payload)
        return

    # Start the config flow
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": MQTT_DISCOVERY_FLOW_STEP},
            data=data
        )
    )


"""
{
  "name": "HID Climate Controller (HW-THID-1234567890123)",
  "unique_id": "HW-THID-1234567890123",
  "device": {
    "identifiers": ["HW-THID-1234567890123"],
    "name": "HID Climate Controller (HW-THID-1234567890123)",
    "model": "HID Climate Controller",
    "manufacturer": "RedPoint",
    "sw_version": "1.0"
  }
}
"""
