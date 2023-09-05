from typing import Any
from enum import Enum


class ClimateServices(Enum):
    TURN_ON = "climate.turn_on"
    TURN_OFF = "climate.turn_off"
    SET_TEMPERATURE = "climate.set_temperature"
    SET_SWING_MODE = "climate.set_swing_mode"
    SET_PRESET_MODE = "climate.set_preset_mode"
    SET_HVAC_MODE = "climate.set_hvac_mode"
    SET_HUMIDITY = "climate.set_humidity"
    SET_FAN_MODE = "climate.set_fan_mode"
    SET_AUX_HEAT = "climate.set_aux_heat"


class ClimateService:
    async def call_service(
        service: ClimateServices, initiator: str, data: dict[str, Any]
    ) -> None:
        pass
