# __init__.py
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .localEight.device import LocalEightSleep

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "switch", "number", "button", "select", "text"]

# Default update interval
UPDATE_INTERVAL = timedelta(seconds=30)


class EightSleepDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to manage data updates from Eight Sleep."""

    def __init__(self, hass: HomeAssistant, client: LocalEightSleep) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="eight_sleep_local_coordinator",
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self):
        """Fetch data from the API."""
        try:
            await self.client.update_device_data()
            return self.client.device_data
        except Exception as err:
            _LOGGER.error("Error updating Eight Sleep local data: %s", err)
            raise err


async def async_setup(hass, config):
    """Set up integration via YAML is not supported; only config flow."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry (created by config flow)."""
    _LOGGER.debug("Setting up eight_sleep_local entry: %s", entry.data)

    host = entry.data.get("host", "localhost")
    port = entry.data.get("port", 3000)

    # Create the API client
    client = LocalEightSleep(host=host, port=port)
    await client.start()

    # Create the coordinator
    coordinator = EightSleepDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    # Store everything in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "sync_states": {
            "sync_mode": False,
            "instant_alarm_sync": False,
        },
        "instant_alarm_settings": {
            "intensity": 80,
            "pattern": "rise",
            "duration": 60,
        },
    }

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        # Stop the client session
        entry_data = hass.data[DOMAIN].pop(entry.entry_id)
        if "client" in entry_data:
            await entry_data["client"].stop()
    return unload_ok