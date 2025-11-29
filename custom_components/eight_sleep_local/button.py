"""Button platform for Eight Sleep Local."""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .switch import SYNC_MODE_KEY, INSTANT_ALARM_SYNC_KEY

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
        # Stop alarm buttons for each side
        EightSleepStopAlarmButton(coordinator, entry.entry_id, "left"),
        EightSleepStopAlarmButton(coordinator, entry.entry_id, "right"),
        # Trigger alarm buttons for each side
        EightSleepTriggerAlarmButton(hass, coordinator, entry.entry_id, "left"),
        EightSleepTriggerAlarmButton(hass, coordinator, entry.entry_id, "right"),
        # Prime pod button (hub device)
        EightSleepPrimeButton(coordinator, entry.entry_id),
    ]

    async_add_entities(entities)


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
        # Check if sync mode is enabled
        entry_data = self.hass.data[DOMAIN][self._entry_id]
        sync_states = entry_data.get("sync_states", {})

        if sync_states.get(SYNC_MODE_KEY, False):
            # Stop both sides
            await self.coordinator.client.stop_alarm("left")
            await self.coordinator.client.stop_alarm("right")
        else:
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
        sync_states = entry_data.get("sync_states", {})
        alarm_settings = entry_data.get("instant_alarm_settings", {})

        intensity = alarm_settings.get("intensity", 80)
        pattern = alarm_settings.get("pattern", "rise")
        duration = alarm_settings.get("duration", 60)

        # Trigger alarm on this side
        await self._coordinator.client.trigger_alarm(
            self._side,
            intensity=intensity,
            pattern=pattern,
            duration=duration
        )

        # If instant alarm sync is enabled, trigger the other side too
        if sync_states.get(INSTANT_ALARM_SYNC_KEY, False):
            other_side = "right" if self._side == "left" else "left"
            await self._coordinator.client.trigger_alarm(
                other_side,
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


class EightSleepPrimeButton(CoordinatorEntity, ButtonEntity):
    """Button to start pod priming."""

    _attr_icon = "mdi:water-sync"

    def __init__(self, coordinator, entry_id: str) -> None:
        """Initialize the prime button."""
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_name = "Eight Sleep Prime Pod"
        self._attr_unique_id = "eight_sleep_prime_pod"

    async def async_press(self) -> None:
        """Handle button press - start priming."""
        await self.coordinator.client.start_priming()
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self):
        """Return device info (hub device)."""
        host = self.coordinator.client._host
        port = self.coordinator.client._port
        return {
            "identifiers": {(DOMAIN, f"eight_sleep_hub_device_{host}_{port}")},
            "name": "Eight Sleep – Hub",
            "manufacturer": "Eight Sleep (Local)",
            "model": "Pod vLocal",
        }
