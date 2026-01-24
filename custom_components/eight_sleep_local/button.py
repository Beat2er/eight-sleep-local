"""Button platform for Eight Sleep Local."""
import logging

from homeassistant.components.button import ButtonEntity
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
    """Set up Eight Sleep button entities."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]

    entities = [
        EightSleepTriggerAlarmButton(hass, coordinator, entry.entry_id, "left"),
        EightSleepTriggerAlarmButton(hass, coordinator, entry.entry_id, "right"),
        EightSleepStopAlarmButton(coordinator, entry.entry_id, "left"),
        EightSleepStopAlarmButton(coordinator, entry.entry_id, "right"),
    ]

    async_add_entities(entities)


class EightSleepTriggerAlarmButton(ButtonEntity):
    """Button to trigger an alarm immediately."""

    _attr_icon = "mdi:alarm"

    def __init__(self, hass: HomeAssistant, coordinator, entry_id: str, side: str) -> None:
        """Initialize the trigger alarm button."""
        self._hass = hass
        self._coordinator = coordinator
        self._side = side
        self._entry_id = entry_id
        self._attr_name = f"Eight Sleep {side.capitalize()} Trigger Alarm"
        self._attr_unique_id = f"eight_sleep_{side}_trigger_alarm"

    async def async_press(self) -> None:
        """Handle button press - trigger the alarm."""
        entry_data = self._hass.data[DOMAIN][self._entry_id]
        alarm_settings = entry_data.get("instant_alarm_settings", {})

        intensity = alarm_settings.get("intensity", 80)
        pattern = alarm_settings.get("pattern", "rise")
        duration = alarm_settings.get("duration", 60)

        await self._coordinator.client.trigger_alarm(
            self._side,
            intensity=intensity,
            pattern=pattern,
            duration=duration
        )
        await self._coordinator.async_request_refresh()

    @property
    def device_info(self):
        """Return device info."""
        host = self._coordinator.client._host
        port = self._coordinator.client._port
        return {
            "identifiers": {(DOMAIN, f"eight_sleep_{self._side}_device_{host}_{port}")},
            "name": f"Eight Sleep – {self._side.capitalize()}",
            "manufacturer": "Eight Sleep (Local)",
            "model": "Pod vLocal",
        }


class EightSleepStopAlarmButton(CoordinatorEntity, ButtonEntity):
    """Button to stop an active alarm."""

    _attr_icon = "mdi:alarm-off"

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the stop alarm button."""
        super().__init__(coordinator)
        self._side = side
        self._entry_id = entry_id
        self._attr_name = f"Eight Sleep {side.capitalize()} Stop Alarm"
        self._attr_unique_id = f"eight_sleep_{side}_stop_alarm"

    async def async_press(self) -> None:
        """Handle button press - stop the alarm."""
        await self.coordinator.client.stop_alarm(self._side)
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
