"""Binary sensor platform for Eight Sleep Local."""
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
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
    """Set up Eight Sleep binary sensor entities."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]

    entities = [
        EightSleepPresenceSensor(coordinator, entry.entry_id, "left"),
        EightSleepPresenceSensor(coordinator, entry.entry_id, "right"),
    ]

    async_add_entities(entities)


class EightSleepPresenceSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for bed presence detection."""

    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_icon = "mdi:bed"

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the presence sensor."""
        super().__init__(coordinator)
        self._side = side
        self._entry_id = entry_id
        self._attr_name = f"Eight Sleep {side.capitalize()} Bed Presence"
        self._attr_unique_id = f"eight_sleep_{side}_bed_presence"

    @property
    def is_on(self) -> bool:
        """Return true if person is present in bed."""
        data = self.coordinator.data or {}
        presence_data = data.get("_presence", {})
        side_presence = presence_data.get(self._side, {})
        return side_presence.get("present", False)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        data = self.coordinator.data or {}
        presence_data = data.get("_presence", {})
        side_presence = presence_data.get(self._side, {})
        return {
            "last_updated": side_presence.get("lastUpdated"),
        }

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
