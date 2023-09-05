from typing import Any

from homeassistant.core import State, ServiceResponse

from .climate_service import ClimateService


class ClimateCommands:
    _SERVICE_TURN_ON = "turn_on"
    _SERVICE_TURN_OFF = "turn_off"
    _SERVICE_SET_TEMPERATURE = "set_temperature"
    _SERVICE_SET_SWING_MODE = "set_swing_mode"
    _SERVICE_SET_PRESET_MODE = "set_preset_mode"
    _SERVICE_SET_HVAC_MODE = "set_hvac_mode"
    _SERVICE_SET_HUMIDITY = "set_humidity"
    _SERVICE_SET_FAN_MODE = "set_fan_mode"
    _SERVICE_SET_AUX_HEAT = "set_aux_heat"

    _service = None

    def __init__(self, service: ClimateService) -> None:
        self._service = service

    def get_state(self, entity_id) -> State | None:
        return self._service.get_state(entity_id)

    async def turn_on(
        self,
        target_entity_id: str,
        triggering_entity_id: str = None,
    ) -> ServiceResponse:
        return await self._service.call(
            service=self._SERVICE_TURN_ON,
            target_entity_id=target_entity_id,
            service_data={},
            triggering_entity_id=triggering_entity_id,
        )

    async def turn_off(
        self, target_entity_id: str, triggering_entity_id: str = None
    ) -> ServiceResponse:
        return await self._service.call(
            service=self._SERVICE_TURN_OFF,
            target_entity_id=target_entity_id,
            service_data={},
            triggering_entity_id=triggering_entity_id,
        )

    async def set_temperature(
        self,
        target_entity_id: str,
        temperature: float,
        target_temp_high: float = None,
        target_temp_low: float = None,
        hvac_mode: str = None,
        triggering_entity_id: str = None,
    ) -> ServiceResponse:
        return await self._service.call(
            service=self._SERVICE_SET_TEMPERATURE,
            target_entity_id=target_entity_id,
            service_data={
                "temperature": temperature,
                "target_temp_high": target_temp_high,
                "target_temp_low": target_temp_low,
                "hvac_mode": hvac_mode,
            },
            triggering_entity_id=triggering_entity_id,
        )

    async def set_swing_mode(
        self, target_entity_id: str, swing_mode: str, triggering_entity_id: str = None
    ) -> ServiceResponse:
        return await self._service.call(
            service=self._SERVICE_SET_SWING_MODE,
            target_entity_id=target_entity_id,
            service_data={"swing_mode": swing_mode},
            triggering_entity_id=triggering_entity_id,
        )

    async def set_preset_mode(
        self, target_entity_id: str, preset_mode: str, triggering_entity_id: str = None
    ) -> ServiceResponse:
        return await self._service.call(
            service=self._SERVICE_SET_PRESET_MODE,
            target_entity_id=target_entity_id,
            service_data={"preset_mode": preset_mode},
            triggering_entity_id=triggering_entity_id,
        )

    async def set_hvac_mode(
        self, target_entity_id: str, hvac_mode: str, triggering_entity_id: str = None
    ) -> ServiceResponse:
        return await self._service.call(
            service=self._SERVICE_SET_HVAC_MODE,
            target_entity_id=target_entity_id,
            service_data={"hvac_mode": hvac_mode},
            triggering_entity_id=triggering_entity_id,
        )

    async def set_humidity(
        self, target_entity_id: str, humidity: int, triggering_entity_id: str = None
    ) -> ServiceResponse:
        return await self._service.call(
            service=self._SERVICE_SET_HUMIDITY,
            target_entity_id=target_entity_id,
            service_data={"humidity": humidity},
            triggering_entity_id=triggering_entity_id,
        )

    async def set_fan_mode(
        self, target_entity_id: str, fan_mode: str, triggering_entity_id: str = None
    ) -> ServiceResponse:
        return await self._service.call(
            service=self._SERVICE_SET_FAN_MODE,
            target_entity_id=target_entity_id,
            service_data={"fan_mode": fan_mode},
            triggering_entity_id=triggering_entity_id,
        )

    async def set_aux_heat(
        self, target_entity_id: str, aux_heat: bool, triggering_entity_id: str = None
    ) -> ServiceResponse:
        return await self._service.call(
            service=self._SERVICE_SET_AUX_HEAT,
            target_entity_id=target_entity_id,
            service_data={"aux_heat": aux_heat},
            triggering_entity_id=triggering_entity_id,
        )
