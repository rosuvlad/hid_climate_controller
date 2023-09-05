from typing import Any

from homeassistant.core import HomeAssistant, Context, State, ServiceResponse

from .utilities import Utilities


class ClimateService:
    _DOMAIN = "climate"

    _hass = None

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    def get_state(self, entity_id) -> State | None:
        return self._hass.states.get(entity_id)

    async def call(
        self,
        service: str,
        target_entity_id: str,
        service_data: dict[str, Any],
        triggering_entity_id: str = None,
    ) -> ServiceResponse:
        parent_id = Utilities.encode_string_as_ulid(triggering_entity_id)
        context = Context(parent_id=parent_id)
        return await self._hass.services.async_call(
            domain=self._DOMAIN,
            service=service,
            target={"entity_id": target_entity_id},
            service_data=service_data,
            context=context,
        )
