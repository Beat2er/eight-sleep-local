"""Select platform for Eight Sleep Local."""
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ALARM_PATTERNS = ["rise", "double"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eight Sleep select entities."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]

    entities = [
        EightSleepAlarmPatternSelect(hass, coordinator, entry.entry_id),
    ]

    async_add_entities(entities)


class EightSleepAlarmPatternSelect(RestoreEntity, SelectEntity):
    """Select entity for instant alarm vibration pattern."""

    _attr_options = ALARM_PATTERNS
    _attr_icon = "mdi:sine-wave"

    def __init__(self, hass: HomeAssistant, coordinator, entry_id: str) -> None:
        """Initialize the alarm pattern select."""
        self._hass = hass
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._attr_name = "Eight Sleep Instant Alarm Pattern"
        self._attr_unique_id = "eight_sleep_instant_alarm_pattern"
        self._current_option = "rise"  # Default

    async def async_added_to_hass(self) -> None:
        """Restore state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in ALARM_PATTERNS:
            self._current_option = last_state.state
            # Update hass.data
            self._hass.data[DOMAIN][self._entry_id]["instant_alarm_settings"]["pattern"] = self._current_option

    @property
    def current_option(self) -> str:
        """Return the current pattern."""
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        """Set the alarm pattern."""
        if option in ALARM_PATTERNS:
            self._current_option = option
            self._hass.data[DOMAIN][self._entry_id]["instant_alarm_settings"]["pattern"] = option
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
