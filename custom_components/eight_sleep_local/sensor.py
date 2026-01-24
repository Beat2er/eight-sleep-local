"""Sensor platform for Eight Sleep Local."""
import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eight Sleep sensor entities."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]

    entities = [
        # Left side sensors
        EightSleepTemperatureSensor(coordinator, entry.entry_id, "left", "current"),
        EightSleepTemperatureSensor(coordinator, entry.entry_id, "left", "target"),
        EightSleepTimeRemainingSensor(coordinator, entry.entry_id, "left"),
        # Right side sensors
        EightSleepTemperatureSensor(coordinator, entry.entry_id, "right", "current"),
        EightSleepTemperatureSensor(coordinator, entry.entry_id, "right", "target"),
        EightSleepTimeRemainingSensor(coordinator, entry.entry_id, "right"),
    ]

    async_add_entities(entities)


class EightSleepTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Sensor for bed temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    def __init__(self, coordinator, entry_id: str, side: str, temp_type: str) -> None:
        """Initialize the temperature sensor."""
        super().__init__(coordinator)
        self._side = side
        self._entry_id = entry_id
        self._temp_type = temp_type  # "current" or "target"

        type_label = "Current" if temp_type == "current" else "Target"
        self._attr_name = f"Eight Sleep {side.capitalize()} {type_label} Temperature"
        self._attr_unique_id = f"eight_sleep_{side}_{temp_type}_temperature"

    @property
    def native_value(self) -> float | None:
        """Return the temperature value."""
        data = self.coordinator.data or {}
        side_data = data.get(self._side, {})
        key = "currentTemperatureF" if self._temp_type == "current" else "targetTemperatureF"
        return side_data.get(key)

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


class EightSleepTimeRemainingSensor(CoordinatorEntity, SensorEntity):
    """Sensor for time remaining."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:timer"

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the time remaining sensor."""
        super().__init__(coordinator)
        self._side = side
        self._entry_id = entry_id
        self._attr_name = f"Eight Sleep {side.capitalize()} Time Remaining"
        self._attr_unique_id = f"eight_sleep_{side}_time_remaining"

    @property
    def native_value(self) -> int | None:
        """Return seconds remaining."""
        data = self.coordinator.data or {}
        side_data = data.get(self._side, {})
        return side_data.get("secondsRemaining")

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
