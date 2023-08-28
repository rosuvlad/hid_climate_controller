from __future__ import annotations

import logging
import json
import voluptuous as vol

from typing import Any
from voluptuous.error import Error
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv, selector
from homeassistant.helpers.service_info.mqtt import MqttServiceInfo
from homeassistant.data_entry_flow import FlowResult, AbortFlow
from json.decoder import JSONDecodeError

from .const import (
    DOMAIN,
    ENTITY_ID_KEY,
    FRIENDLY_NAME_KEY,
    DEVICE_UNIQUE_ID_KEY,
    DEVICE_NAME_KEY,
    DEVICE_DEFERRED_REGISTRATION_KEY,
    CONTROLLER_KEY,
    CONTROLLER_ENTITY_ID,
    CONTROLLER_NAME,
    CLIMATE_KEY,
    CLIMATE_ENTITY_ID,
    CLIMATE_ENTITY_TYPE,
    BASE_ERROR,
    DEVICE_ALREADY_CONFIGURED_ERROR,
    MQTT_DISCOVERY_STEP_INVALID_DISCOVERY_PAYLOAD_ERROR,
    MQTT_DISCOVERY_STEP_DEVICE_VALIDATION_FAILURE_ERROR,
    MQTT_DISCOVERY_STEP_UNKNOWN_FAILURE_ERROR,
    USER_INPUT_STEP_UNKNOWN_FAILURE_ERROR,
)

_LOGGER = logging.getLogger(__name__)

UNIQUE_ID_PATTERN = r"^TC-HID-[A-Za-z0-9]{17}$"

DISCOVERY_CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(DEVICE_UNIQUE_ID_KEY): vol.All(
            cv.string, vol.Match(UNIQUE_ID_PATTERN)
        ),
        vol.Optional(DEVICE_NAME_KEY): str,
    },
    extra=vol.ALLOW_EXTRA,
)


def generate_user_config_schema(data: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            CONTROLLER_ENTITY_ID: vol.Required(
                str, default=data.get(DEVICE_UNIQUE_ID_KEY)
            ),
            CONTROLLER_NAME: vol.Optional(str, default=data.get(DEVICE_NAME_KEY)),
            vol.Required(CLIMATE_ENTITY_ID): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=CLIMATE_ENTITY_TYPE),
            ),
        }
    )


@config_entries.HANDLERS.register(DOMAIN)
class HidClimateControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    _discovery_config = None

    async def async_step_mqtt(
        self, discovery_info: MqttServiceInfo | None = None
    ) -> FlowResult:
        unique_id = None

        try:
            discovery_config = json.loads(discovery_info.payload)

            DISCOVERY_CONFIG_SCHEMA(discovery_config)

            unique_id = discovery_config[DEVICE_UNIQUE_ID_KEY]

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            self._discovery_config = {
                **discovery_config,
                DEVICE_UNIQUE_ID_KEY: unique_id,
                DEVICE_NAME_KEY: discovery_config.get(DEVICE_NAME_KEY),
                DEVICE_DEFERRED_REGISTRATION_KEY: False,
            }

            _LOGGER.info("Triggering user step for %s", self._discovery_config)
            return await self.async_step_user()
        except JSONDecodeError as ex:
            _LOGGER.error(
                f"MQTT discovery registration failed because of malformed payload. MQTT Payload: {discovery_info.payload}",
                ex,
            )
            return self.async_abort(
                reason=MQTT_DISCOVERY_STEP_INVALID_DISCOVERY_PAYLOAD_ERROR
            )
        except Error as ex:
            _LOGGER.error(
                f"MQTT discovery registration failed because of validation errors. MQTT Payload: {discovery_info.payload}",
                ex,
            )
            return self.async_abort(
                reason=MQTT_DISCOVERY_STEP_DEVICE_VALIDATION_FAILURE_ERROR
            )
        except AbortFlow as ex:
            return self.async_abort(
                reason=DEVICE_ALREADY_CONFIGURED_ERROR,
                description_placeholders={DEVICE_UNIQUE_ID_KEY: unique_id},
            )
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.error("Unknown exception encoutered", ex)
            return self.async_abort(reason=MQTT_DISCOVERY_STEP_UNKNOWN_FAILURE_ERROR)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        unique_id = None
        errors = {}

        if not self._discovery_config:
            self._discovery_config = {
                DEVICE_DEFERRED_REGISTRATION_KEY: True,
            }

        if user_input is not None:
            try:
                unique_id = user_input.get(CONTROLLER_ENTITY_ID)

                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                controller_config = {
                    ENTITY_ID_KEY: unique_id,
                    FRIENDLY_NAME_KEY: user_input.get(CONTROLLER_NAME) or unique_id,
                    DEVICE_DEFERRED_REGISTRATION_KEY: self._discovery_config.get(
                        DEVICE_DEFERRED_REGISTRATION_KEY, True
                    ),
                }

                climate_entity_id = user_input.get(CLIMATE_ENTITY_ID)
                climate_states = self.hass.states.get(climate_entity_id)
                climate_friendly_name = climate_states.attributes.get(
                    FRIENDLY_NAME_KEY, climate_entity_id
                )

                climate_config = {
                    ENTITY_ID_KEY: climate_entity_id,
                    FRIENDLY_NAME_KEY: climate_friendly_name,
                }

                config = {
                    CONTROLLER_KEY: controller_config,
                    CLIMATE_KEY: climate_config,
                }

                _LOGGER.info("Creating config entry for %s", config)

                return self.async_create_entry(
                    title=config.get(CONTROLLER_KEY, {}).get(FRIENDLY_NAME_KEY),
                    description=f"Paired to {config.get(CLIMATE_KEY, {}).get(FRIENDLY_NAME_KEY)}",
                    data=config,
                )
            except AbortFlow as ex:
                return self.async_abort(
                    reason=DEVICE_ALREADY_CONFIGURED_ERROR,
                    description_placeholders={CONTROLLER_ENTITY_ID: unique_id},
                )
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.error("Unknown exception encoutered", ex)
                errors[BASE_ERROR] = USER_INPUT_STEP_UNKNOWN_FAILURE_ERROR

        config_schema = generate_user_config_schema(self._discovery_config)

        return self.async_show_form(
            step_id="user",
            data_schema=config_schema,
            errors=errors,
        )


"""
Topic: homeassistant/hid_climate_controller/HW-THID-1234567890123/config
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
