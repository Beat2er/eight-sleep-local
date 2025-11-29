# __init__.py
import logging
from datetime import timedelta, datetime, timezone

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .localEight.device import LocalEightSleep

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "switch", "number", "button", "select", "text"]

# Default update interval for device status
UPDATE_INTERVAL = timedelta(seconds=30)
# Health metrics update interval (minimum 60s since data only updates every 60s)
HEALTH_UPDATE_INTERVAL = timedelta(seconds=60)


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
            # Also fetch presence data
            presence = await self.client.get_presence()
            return {
                **self.client.device_data,
                "_presence": presence or {"left": {"present": False}, "right": {"present": False}},
            }
        except Exception as err:
            _LOGGER.error("Error updating Eight Sleep local data: %s", err)
            raise err


class EightSleepHealthCoordinator(DataUpdateCoordinator):
    """Coordinator to manage health metrics data updates."""

    def __init__(self, hass: HomeAssistant, client: LocalEightSleep) -> None:
        """Initialize the health coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="eight_sleep_health_coordinator",
            update_interval=HEALTH_UPDATE_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self):
        """Fetch health metrics from the API."""
        try:
            # Get most recent sleep records to determine time range
            sleep_records = await self.client.get_sleep_records() or []

            # Get the most recent sleep record for each side
            left_sleep = None
            right_sleep = None
            for record in sleep_records:
                if record.get("side") == "left" and left_sleep is None:
                    left_sleep = record
                elif record.get("side") == "right" and right_sleep is None:
                    right_sleep = record
                if left_sleep and right_sleep:
                    break

            # Fetch vitals summary for each side using sleep record time range
            left_summary = None
            right_summary = None

            if left_sleep:
                left_summary = await self.client.get_vitals_summary(
                    side="left",
                    start_time=left_sleep.get("entered_bed_at"),
                    end_time=left_sleep.get("left_bed_at"),
                )

            if right_sleep:
                right_summary = await self.client.get_vitals_summary(
                    side="right",
                    start_time=right_sleep.get("entered_bed_at"),
                    end_time=right_sleep.get("left_bed_at"),
                )

            return {
                "left": {
                    "sleep": left_sleep,
                    "vitals_summary": left_summary,
                },
                "right": {
                    "sleep": right_sleep,
                    "vitals_summary": right_summary,
                },
            }
        except Exception as err:
            _LOGGER.error("Error updating Eight Sleep health data: %s", err)
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

    # Create the coordinators
    coordinator = EightSleepDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    health_coordinator = EightSleepHealthCoordinator(hass, client)
    await health_coordinator.async_config_entry_first_refresh()

    # Store everything in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        "health_coordinator": health_coordinator,
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