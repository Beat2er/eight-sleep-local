"""Switch platform for Eight Sleep Local."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Keys for storing sync states in hass.data
SYNC_MODE_KEY = "sync_mode"
INSTANT_ALARM_SYNC_KEY = "instant_alarm_sync"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eight Sleep switches."""
    # Get coordinator from hass.data (created in __init__.py)
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]

    entities = [
        # Power switches for each side
        EightSleepPowerSwitch(coordinator, entry.entry_id, "left"),
        EightSleepPowerSwitch(coordinator, entry.entry_id, "right"),
        # Sync mode switches (hub device)
        EightSleepSyncModeSwitch(hass, coordinator, entry.entry_id, SYNC_MODE_KEY, "Sync Mode"),
        EightSleepSyncModeSwitch(hass, coordinator, entry.entry_id, INSTANT_ALARM_SYNC_KEY, "Instant Alarm Sync"),
    ]

    async_add_entities(entities)


class EightSleepPowerSwitch(CoordinatorEntity, SwitchEntity):
    """Switch to turn bed side on/off."""

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the power switch."""
        super().__init__(coordinator)
        self._side = side
        self._entry_id = entry_id
        self._attr_name = f"Eight Sleep {side.capitalize()} Power"
        self._attr_unique_id = f"eight_sleep_{side}_power"
        self._attr_icon = "mdi:power"

    @property
    def is_on(self) -> bool:
        """Return true if the side is on."""
        data = self.coordinator.data or {}
        side_data = data.get(self._side, {})
        return side_data.get("isOn", False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the bed side."""
        # Check if sync mode is enabled
        entry_data = self.hass.data[DOMAIN][self._entry_id]
        sync_states = entry_data.get("sync_states", {})
        if sync_states.get(SYNC_MODE_KEY, False):
            # Turn on both sides
            await self.coordinator.client.turn_on("left")
            await self.coordinator.client.turn_on("right")
        else:
            await self.coordinator.client.turn_on(self._side)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the bed side."""
        # Check if sync mode is enabled
        entry_data = self.hass.data[DOMAIN][self._entry_id]
        sync_states = entry_data.get("sync_states", {})
        if sync_states.get(SYNC_MODE_KEY, False):
            # Turn off both sides
            await self.coordinator.client.turn_off("left")
            await self.coordinator.client.turn_off("right")
        else:
            await self.coordinator.client.turn_off(self._side)
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


class EightSleepSyncModeSwitch(RestoreEntity, SwitchEntity):
    """Switch for sync mode settings (stored locally, not on device)."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator,
        entry_id: str,
        sync_key: str,
        name: str,
    ) -> None:
        """Initialize the sync mode switch."""
        self._hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._sync_key = sync_key
        self._attr_name = f"Eight Sleep {name}"
        self._attr_unique_id = f"eight_sleep_{sync_key}"
        self._attr_icon = "mdi:sync" if sync_key == SYNC_MODE_KEY else "mdi:alarm-multiple"
        self._is_on = False

    async def async_added_to_hass(self) -> None:
        """Restore state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state == "on"
            # Update hass.data with restored state
            entry_data = self._hass.data[DOMAIN].get(self._entry_id, {})
            if "sync_states" in entry_data:
                entry_data["sync_states"][self._sync_key] = self._is_on

    @property
    def is_on(self) -> bool:
        """Return true if sync mode is enabled."""
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        """Enable sync mode."""
        self._is_on = True
        self._hass.data[DOMAIN][self._entry_id]["sync_states"][self._sync_key] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable sync mode."""
        self._is_on = False
        self._hass.data[DOMAIN][self._entry_id]["sync_states"][self._sync_key] = False
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
