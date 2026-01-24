"""Number platform for Eight Sleep Local."""
import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eight Sleep number entities."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]

    entities = [
        EightSleepAlarmIntensityNumber(hass, coordinator, entry.entry_id),
        EightSleepAlarmDurationNumber(hass, coordinator, entry.entry_id),
    ]

    async_add_entities(entities)


class EightSleepAlarmIntensityNumber(RestoreEntity, NumberEntity):
    """Number entity for instant alarm vibration intensity."""

    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:vibrate"

    def __init__(self, hass: HomeAssistant, coordinator, entry_id: str) -> None:
        """Initialize the alarm intensity number."""
        self._hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._attr_name = "Eight Sleep Alarm Intensity"
        self._attr_unique_id = "eight_sleep_alarm_intensity"
        self._value = 80  # Default

    async def async_added_to_hass(self) -> None:
        """Restore state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._value = int(float(last_state.state))
                self._hass.data[DOMAIN][self._entry_id]["instant_alarm_settings"]["intensity"] = self._value
            except (ValueError, TypeError):
                pass

    @property
    def native_value(self) -> float:
        """Return the current intensity."""
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        """Set the alarm intensity."""
        self._value = int(value)
        self._hass.data[DOMAIN][self._entry_id]["instant_alarm_settings"]["intensity"] = self._value
        self.async_write_ha_state()

    @property
    def device_info(self):
        """Return device info (hub device)."""
        host = self._coordinator.client._host
        port = self._coordinator.client._port
        return {
            "identifiers": {(DOMAIN, f"eight_sleep_hub_device_{host}_{port}")},
            "name": "Eight Sleep – Hub",
            "manufacturer": "Eight Sleep (Local)",
            "model": "Pod vLocal",
        }


class EightSleepAlarmDurationNumber(RestoreEntity, NumberEntity):
    """Number entity for instant alarm duration."""

    _attr_native_min_value = 10
    _attr_native_max_value = 180
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "s"
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:timer"

    def __init__(self, hass: HomeAssistant, coordinator, entry_id: str) -> None:
        """Initialize the alarm duration number."""
        self._hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._attr_name = "Eight Sleep Alarm Duration"
        self._attr_unique_id = "eight_sleep_alarm_duration"
        self._value = 60  # Default

    async def async_added_to_hass(self) -> None:
        """Restore state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._value = int(float(last_state.state))
                self._hass.data[DOMAIN][self._entry_id]["instant_alarm_settings"]["duration"] = self._value
            except (ValueError, TypeError):
                pass

    @property
    def native_value(self) -> float:
        """Return the current duration."""
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        """Set the alarm duration."""
        self._value = int(value)
        self._hass.data[DOMAIN][self._entry_id]["instant_alarm_settings"]["duration"] = self._value
        self.async_write_ha_state()

    @property
    def device_info(self):
        """Return device info (hub device)."""
        host = self._coordinator.client._host
        port = self._coordinator.client._port
        return {
            "identifiers": {(DOMAIN, f"eight_sleep_hub_device_{host}_{port}")},
            "name": "Eight Sleep – Hub",
            "manufacturer": "Eight Sleep (Local)",
            "model": "Pod vLocal",
        }
