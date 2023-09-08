from __future__ import annotations

import logging
import asyncio
import json

from typing import Any
from json.decoder import JSONDecodeError

from homeassistant.core import HomeAssistant
from homeassistant.components import mqtt

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MqttMessageWithAck:
    def __init__(
        self,
        hass: HomeAssistant,
        command_topic: str,
        ack_topic: str,
        timeout: int = 10,
    ) -> None:
        self._hass = hass
        self._command_topic = command_topic
        self._ack_topic = ack_topic
        self._timeout = timeout

    async def send(self, data: Any) -> Any | None:
        ack_received_event = self._hass.loop.create_future()

        async def ack_callback(msg):
            try:
                if msg.payload is None:
                    ack_received_event.set_result(None)
                else:
                    payload = json.loads(msg.payload)
                    ack_received_event.set_result(payload)

            except JSONDecodeError as ex:
                _LOGGER.error("Failed to decode JSON payload: %s", ex)
                ack_received_event.set_exception(ex)

        unsubscribe_ack = await mqtt.async_subscribe(
            self._hass, self._ack_topic, lambda: ack_callback, 1
        )

        payload_string = json.dumps(data)

        await mqtt.async_publish(self._hass, self._command_topic, payload_string)

        try:
            return await asyncio.wait_for(
                self.ack_received_event, timeout=self._timeout / 1000
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Timeout waiting for ACK on topic {self._ack_topic}")
        finally:
            if unsubscribe_ack:
                unsubscribe_ack()
                unsubscribe_ack = None
