"""Config flow for HID Climate Controller integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from typing import Any
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, AbortFlow

from .validations import ValidationException
from .device_validation import DeviceValidation
from .const import (
    DOMAIN,
    USER_FLOW_STEP,
    CLIMATE_ENTITY_SELECTION_FLOW_STEP,
    UNIQUE_ID_KEY,
    ENTITY_ID_KEY,
    FRIENDLY_NAME_KEY,
    CONTROLLER_KEY,
    CLIMATE_KEY,
    DEFERRED_REGISTRATION_KEY,
    CLIMATE_ENTITY_TYPE,
    MQTT_DISCOVERY_STEP_DEVICE_VALIDATION_FAILURE_ERROR,
    MQTT_DISCOVERY_STEP_UNKNOWN_FAILURE_ERROR,
    USER_INPUT_STEP_UNKNOWN_FAILURE_ERROR,
    CLIMATE_ENTITY_SELECTION_STEP_NO_AVAILABLE_ENTITIES_ERROR,
    CLIMATE_ENTITY_SELECTION_STEP_VALIDATION_FAILURE_ERROR,
    CLIMATE_ENTITY_SELECTION_STEP_UNKNOWN_FAILURE_ERROR
)

_LOGGER = logging.getLogger(__name__)

CONTROLLER_CONFIG_SCHEMA = vol.Schema({vol.Required(UNIQUE_ID_KEY): str})


async def get_all_entities_of_type_as_dict(
    hass: HomeAssistant, entityType: str
) -> dict[str, str]:
    climate_entities = hass.states.async_entity_ids(entityType)

    return {
        entity_id: hass.states.get(entity_id).attributes.get(
            FRIENDLY_NAME_KEY, entity_id)
        for entity_id in climate_entities
    }


async def get_entity_selector_schema(
    fieldName: str, entities: dict[str, str]
) -> vol.Schema:
    return vol.Schema({vol.Required(fieldName): vol.In(entities)})


def validate_climate_entity_config(data: dict[str, Any]) -> None:
    entity_id = data.get(ENTITY_ID_KEY)

    if not entity_id or len(entity_id) == 0:
        raise ValidationException(
            CLIMATE_ENTITY_SELECTION_STEP_VALIDATION_FAILURE_ERROR)


@config_entries.HANDLERS.register(DOMAIN)
class HIDClimateControllerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    _controller_config = None
    _climate_config = None

    async def async_step_mqtt_discovery(self, data: dict[str, Any] | None = None) -> FlowResult:
        try:
            DeviceValidation.validate_device(data)

            unique_id = data[UNIQUE_ID_KEY]

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            data[DEFERRED_REGISTRATION_KEY] = False

            self._controller_config = data
        except ValidationException as ex:
            _LOGGER.warning(
                "Registration failed because of validation errors. Exception: %s. Payload: %s", ex, data)
            return self.async_abort(reason=MQTT_DISCOVERY_STEP_DEVICE_VALIDATION_FAILURE_ERROR)
        except AbortFlow as ex:
            raise ex
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.warning("Unknown exception encoutered. Exception: %s", ex)
            return self.async_abort(reason=MQTT_DISCOVERY_STEP_UNKNOWN_FAILURE_ERROR)

        return await self.async_step_climate_entity_selection()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors = {}

        if user_input is not None:
            try:
                DeviceValidation.validate_device(user_input)

                unique_id = user_input[UNIQUE_ID_KEY]

                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                user_input[DEFERRED_REGISTRATION_KEY] = True

                self._controller_config = user_input

            except ValidationException as ex:
                _LOGGER.warning(
                    "Configuration failed because of validation errors. Exception: %s", ex)
                errors[ex.reason] = ex.reason
            except AbortFlow as ex:
                raise ex
            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.warning(
                    "Unknown exception encoutered. Exception: %s", ex)
                errors[USER_INPUT_STEP_UNKNOWN_FAILURE_ERROR] = USER_INPUT_STEP_UNKNOWN_FAILURE_ERROR

            if len(errors) == 0:
                return await self.async_step_climate_entity_selection()

        return self.async_show_form(
            step_id=USER_FLOW_STEP,
            data_schema=CONTROLLER_CONFIG_SCHEMA,
            errors=errors,
        )

    async def async_step_climate_entity_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors = {}

        climate_entities = await get_all_entities_of_type_as_dict(self.hass, CLIMATE_ENTITY_TYPE)
        if len(climate_entities) == 0:
            return self.async_abort(reason=CLIMATE_ENTITY_SELECTION_STEP_NO_AVAILABLE_ENTITIES_ERROR)

        if user_input is not None:
            data = None

            try:
                validate_climate_entity_config(user_input)

                user_input[FRIENDLY_NAME_KEY] = climate_entities.get(
                    user_input[ENTITY_ID_KEY], user_input[ENTITY_ID_KEY])

                data = {
                    "controller":  self._controller_config,
                    "climate": user_input
                }
            except ValidationException as ex:
                _LOGGER.warning(
                    "Climate entity selection failed because of validation errors. Exception: %s", ex)
                errors[ex.reason] = ex.reason
            except Exception:  # pylint: disable=broad-except
                _LOGGER.warning(
                    "Unknown exception encoutered. Exception: %s", ex)
                errors[CLIMATE_ENTITY_SELECTION_STEP_UNKNOWN_FAILURE_ERROR] = CLIMATE_ENTITY_SELECTION_STEP_UNKNOWN_FAILURE_ERROR

            if len(errors) == 0:
                return self.async_create_entry(
                    title=data[CONTROLLER_KEY][UNIQUE_ID_KEY],
                    description=f'Paired to {data[CLIMATE_KEY][FRIENDLY_NAME_KEY]}',
                    data=data
                )

        placeholders = {
            UNIQUE_ID_KEY: self._controller_config[UNIQUE_ID_KEY]
        }

        schema = await get_entity_selector_schema(ENTITY_ID_KEY, climate_entities)

        return self.async_show_form(
            step_id=CLIMATE_ENTITY_SELECTION_FLOW_STEP,
            description_placeholders=placeholders,
            data_schema=schema,
            errors=errors,
        )
