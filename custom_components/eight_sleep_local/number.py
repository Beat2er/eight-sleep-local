"""Number platform for Eight Sleep Local."""
import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .switch import SYNC_MODE_KEY

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
        # Temperature controls for each side
        EightSleepTemperatureNumber(coordinator, entry.entry_id, "left"),
        EightSleepTemperatureNumber(coordinator, entry.entry_id, "right"),
        # Instant alarm settings (hub device)
        EightSleepAlarmIntensityNumber(hass, coordinator, entry.entry_id),
        EightSleepAlarmDurationNumber(hass, coordinator, entry.entry_id),
    ]

    async_add_entities(entities)


class EightSleepTemperatureNumber(CoordinatorEntity, NumberEntity):
    """Number entity for setting bed temperature."""

    _attr_native_min_value = 55
    _attr_native_max_value = 110
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "°F"
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:thermometer"

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the temperature number."""
        super().__init__(coordinator)
        self._side = side
        self._entry_id = entry_id
        self._attr_name = f"Eight Sleep {side.capitalize()} Temperature"
        self._attr_unique_id = f"eight_sleep_{side}_temperature"

    @property
    def native_value(self) -> float | None:
        """Return the current target temperature."""
        data = self.coordinator.data or {}
        side_data = data.get(self._side, {})
        return side_data.get("targetTemperatureF")

    async def async_set_native_value(self, value: float) -> None:
        """Set the target temperature."""
        temp = int(value)

        # Check if sync mode is enabled
        entry_data = self.hass.data[DOMAIN][self._entry_id]
        sync_states = entry_data.get("sync_states", {})

        if sync_states.get(SYNC_MODE_KEY, False):
            # Set both sides
            await self.coordinator.client.set_temperature("left", temp)
            await self.coordinator.client.set_temperature("right", temp)
        else:
            await self.coordinator.client.set_temperature(self._side, temp)

        await self.coordinator.async_request_refresh()

    @property
    def device_info(self):
        """Return device info."""
        host = self.coordinator.client._host
        port = self.coordinator.client._port
        return {
            "identifiers": {(DOMAIN, f"eight_sleep_{self._side}_device_{host}_{port}")},
            "name": f"Eight Sleep – {self._side.capitalize()}",
            "manufacturer": "Eight Sleep (Local)",
            "model": "Pod vLocal",
        }


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
        self._attr_name = "Eight Sleep Instant Alarm Intensity"
        self._attr_unique_id = "eight_sleep_instant_alarm_intensity"
        self._value = 80  # Default

    async def async_added_to_hass(self) -> None:
        """Restore state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._value = int(float(last_state.state))
                # Update hass.data
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

    _attr_native_min_value = 0
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
        self._attr_name = "Eight Sleep Instant Alarm Duration"
        self._attr_unique_id = "eight_sleep_instant_alarm_duration"
        self._value = 60  # Default

    async def async_added_to_hass(self) -> None:
        """Restore state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state not in (None, "unknown", "unavailable"):
            try:
                self._value = int(float(last_state.state))
                # Update hass.data
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
