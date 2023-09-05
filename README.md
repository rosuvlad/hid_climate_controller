# hid_climate_controller
HomeAssistant HID Climate Controller


Topic: homeassistant/hid_climate_controller/HW-THID-12345678901231111/config


Payload:

```
{
  "name": "HW-THID-12345678901231111",
  "unique_id": "HW-THID-12345678901231111",
  "device": {
    "model": "HID Climate Controller",
    "manufacturer": "rosuvlad",
    "sw_version": "1.0.0",
    "hw_version": "1.0.0"
  }
}
```


```
parent_id = UlidUtilities.encode_string_as_ulid("test")
_LOGGER.info("Encoded parent_id: %s", parent_id)
context = Context(parent_id=parent_id)

await self._hass.services.async_call(
    domain="climate",
    service="turn_on",
    target={"entity_id": self._entity_id},
    service_data={},
    context=context,
)
```