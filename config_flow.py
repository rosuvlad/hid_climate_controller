from __future__ import annotations

import logging
import json
import voluptuous as vol

from typing import Any
from json.decoder import JSONDecodeError
from voluptuous.error import Error

from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv, selector
from homeassistant.helpers.service_info.mqtt import MqttServiceInfo
from homeassistant.data_entry_flow import FlowResult, AbortFlow

from .validators import validate_discovery_info, validate_config
from .const import (
    DOMAIN,
    ENTITY_ID_KEY,
    FRIENDLY_NAME_KEY,
    DEVICE_KEY,
    DEVICE_UNIQUE_ID_KEY,
    DEVICE_NAME_KEY,
    DEVICE_DEFERRED_REGISTRATION_KEY,
    CONTROLLER_KEY,
    CONTROLLER_ENTITY_ID_KEY,
    CONTROLLER_NAME_KEY,
    CLIMATE_KEY,
    CLIMATE_ENTITY_ID_KEY,
    CLIMATE_ENTITY_TYPE,
    UNKNOWN_EXCEPTION_ERROR,
    BASE_ERROR_PLACEHOLDER,
    DEVICE_CONFIG_UPDATED,
    DEVICE_ALREADY_CONFIGURED_ERROR,
    MQTT_DISCOVERY_STEP_INVALID_DISCOVERY_PAYLOAD_ERROR,
    MQTT_DISCOVERY_STEP_DEVICE_VALIDATION_FAILURE_ERROR,
    MQTT_DISCOVERY_STEP_UNKNOWN_FAILURE_ERROR,
    USER_INPUT_STEP_UNKNOWN_FAILURE_ERROR,
)

_LOGGER = logging.getLogger(__name__)


def generate_config_schema(data: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONTROLLER_ENTITY_ID_KEY, default=data.get(DEVICE_UNIQUE_ID_KEY) or ""
            ): cv.string,
            vol.Optional(
                CONTROLLER_NAME_KEY,
                default=data.get(DEVICE_NAME_KEY)
                or data.get(DEVICE_UNIQUE_ID_KEY)
                or "",
            ): cv.string,
            vol.Required(CLIMATE_ENTITY_ID_KEY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=CLIMATE_ENTITY_TYPE),
            ),
        }
    )


@config_entries.HANDLERS.register(DOMAIN)
class HIDClimateControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    _discovery_config = None

    async def async_step_mqtt(
        self, discovery_info: MqttServiceInfo | None = None
    ) -> FlowResult:
        _LOGGER.debug(
            "Running async_step_mqtt to register device via MQTT discovery - discovery_info: %s",
            discovery_info,
        )

        errors = {}
        unique_id = None

        try:
            discovery_config = json.loads(discovery_info.payload)
            _LOGGER.debug(
                "Successfully parsed MQTT discovery payload: %s", discovery_config
            )

            errors = validate_discovery_info(discovery_config)
            if len(errors) > 0:
                raise Error
            _LOGGER.debug("Successfully validated MQTT discovery payload")

            unique_id = discovery_config[DEVICE_UNIQUE_ID_KEY]
            _LOGGER.debug(
                "Extracted unique_id from MQTT discovery payload: %s", unique_id
            )

            config_entry = await self.async_set_unique_id(unique_id)
            controller_config = (
                {} if not config_entry else config_entry.data.get(CONTROLLER_KEY, {})
            )
            controller_deferred_registration = controller_config.get(
                DEVICE_DEFERRED_REGISTRATION_KEY, False
            )
            if config_entry and controller_deferred_registration:
                _LOGGER.debug(
                    "Device with unique_id %s is already registered with deferred registration is pending. Finishing up the pending registration process",
                    unique_id,
                )

            device_config = discovery_config.get(DEVICE_KEY, {})

            self._discovery_config = {
                DEVICE_UNIQUE_ID_KEY: unique_id,
                DEVICE_NAME_KEY: discovery_config.get(DEVICE_NAME_KEY),
                DEVICE_KEY: device_config,
                DEVICE_DEFERRED_REGISTRATION_KEY: False,
            }

            _LOGGER.debug(
                "Compiled discovery config: %s. Moving forwarad to async_step_user",
                self._discovery_config,
            )

            if not controller_deferred_registration:
                self._abort_if_unique_id_configured()
                return await self.async_step_user()

            config = {**config_entry.data}
            config.update(
                {
                    CONTROLLER_KEY: {
                        ENTITY_ID_KEY: unique_id,
                        FRIENDLY_NAME_KEY: discovery_config.get(DEVICE_NAME_KEY)
                        or unique_id,
                        DEVICE_KEY: device_config,
                        DEVICE_DEFERRED_REGISTRATION_KEY: False,
                    }
                }
            )
            self.hass.config_entries.async_update_entry(config_entry, data=config)
            await self.hass.config_entries.async_reload(config_entry.entry_id)
            return self.async_abort(reason=DEVICE_CONFIG_UPDATED)
        except JSONDecodeError as ex:
            _LOGGER.error(
                "MQTT discovery registration failed because of malformed payload. Exception: %s. MQTT Payload: %s",
                ex,
                discovery_info.payload,
            )
            return self.async_abort(
                reason=MQTT_DISCOVERY_STEP_INVALID_DISCOVERY_PAYLOAD_ERROR
            )
        except Error as ex:
            _LOGGER.error(
                "MQTT discovery registration failed because of validation errors. Errors: %s. MQTT Payload: %s",
                errors,
                discovery_info.payload,
            )
            return self.async_abort(
                reason=MQTT_DISCOVERY_STEP_DEVICE_VALIDATION_FAILURE_ERROR
            )
        except AbortFlow as ex:
            _LOGGER.debug(
                "MQTT discovery registration skipped because device is already registered. Unique ID: %s",
                unique_id,
            )

            return self.async_abort(reason=DEVICE_ALREADY_CONFIGURED_ERROR)
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.error(UNKNOWN_EXCEPTION_ERROR, ex)

            return self.async_abort(reason=MQTT_DISCOVERY_STEP_UNKNOWN_FAILURE_ERROR)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        _LOGGER.debug(
            "Running async_step_user to register device via user input - user_input: %s",
            user_input,
        )

        errors = {}
        unique_id = None

        if not self._discovery_config:
            _LOGGER.debug(
                "No discovery config found. Compiling a default one with deferred registration enabled"
            )

            self._discovery_config = {
                DEVICE_DEFERRED_REGISTRATION_KEY: True,
            }

        if user_input is not None:
            errors = validate_config(user_input)
            if len(errors) == 0:
                try:
                    unique_id = user_input.get(CONTROLLER_ENTITY_ID_KEY)

                    _LOGGER.debug("Extracted unique_id from user input: %s", unique_id)

                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()

                    _LOGGER.debug(
                        "Flagged %s unique_id as registration in progress", unique_id
                    )

                    device_config = self._discovery_config.get(DEVICE_KEY, {})

                    controller_config = {
                        ENTITY_ID_KEY: unique_id,
                        FRIENDLY_NAME_KEY: user_input.get(CONTROLLER_NAME_KEY)
                        or unique_id,
                        DEVICE_KEY: device_config,
                        DEVICE_DEFERRED_REGISTRATION_KEY: self._discovery_config.get(
                            DEVICE_DEFERRED_REGISTRATION_KEY, True
                        ),
                    }

                    climate_entity_id = user_input.get(CLIMATE_ENTITY_ID_KEY)
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

                    _LOGGER.debug(
                        "Compiled config: %s. ConfigFlow completed successfully and moving forward to async_create_entry",
                        config,
                    )

                    return self.async_create_entry(
                        title=config.get(CONTROLLER_KEY, {}).get(ENTITY_ID_KEY),
                        description=f"Linked to {config.get(CLIMATE_KEY, {}).get(FRIENDLY_NAME_KEY) or config.get(CLIMATE_KEY, {}).get(ENTITY_ID_KEY)}",
                        data=config,
                    )
                except AbortFlow as ex:
                    _LOGGER.debug(
                        "User input registration skipped because device is already registered. Unique ID: %s",
                        unique_id,
                    )

                    return self.async_abort(reason=DEVICE_ALREADY_CONFIGURED_ERROR)
                except Exception as ex:  # pylint: disable=broad-except
                    _LOGGER.error("Unknown exception encoutered", ex)

                    errors[
                        BASE_ERROR_PLACEHOLDER
                    ] = USER_INPUT_STEP_UNKNOWN_FAILURE_ERROR

        _LOGGER.debug(
            "Compiling data schema with discovery config: %s and errors: %s",
            self._discovery_config,
            errors,
        )

        data_schema = generate_config_schema(self._discovery_config)

        _LOGGER.debug("Showing form with data schema: %s", data_schema)

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
