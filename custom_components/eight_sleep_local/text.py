"""Text platform for Eight Sleep Local."""
import json
import logging

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DAYS_OF_WEEK = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eight Sleep text entities."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]

    entities = [
        EightSleepAlarmScheduleText(coordinator, entry.entry_id, "left"),
        EightSleepAlarmScheduleText(coordinator, entry.entry_id, "right"),
    ]

    async_add_entities(entities)


class EightSleepAlarmScheduleText(CoordinatorEntity, TextEntity):
    """Text entity for alarm schedule JSON configuration."""

    _attr_mode = TextMode.TEXT
    _attr_icon = "mdi:calendar-clock"
    _attr_native_max = 4096  # Allow enough space for JSON

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the alarm schedule text entity."""
        super().__init__(coordinator)
        self._side = side
        self._entry_id = entry_id
        self._attr_name = f"Eight Sleep {side.capitalize()} Alarm Schedule"
        self._attr_unique_id = f"eight_sleep_{side}_alarm_schedule"
        self._cached_schedule: dict | None = None

    @property
    def native_value(self) -> str:
        """Return the current alarm schedule as JSON."""
        if self._cached_schedule:
            return json.dumps(self._cached_schedule, indent=2)
        return "{}"

    async def async_update(self) -> None:
        """Update the schedule from the API."""
        await super().async_update()
        await self._fetch_schedule()

    async def _fetch_schedule(self) -> None:
        """Fetch the schedule from the API and cache it."""
        try:
            schedules = await self.coordinator.client.get_schedules()
            if schedules and self._side in schedules:
                side_schedule = schedules[self._side]
                # Extract just alarm data for each day
                alarm_schedule = {}
                for day in DAYS_OF_WEEK:
                    if day in side_schedule and "alarm" in side_schedule[day]:
                        alarm_schedule[day] = side_schedule[day]["alarm"]
                self._cached_schedule = alarm_schedule
        except Exception as err:
            _LOGGER.error("Error fetching schedule: %s", err)

    async def async_added_to_hass(self) -> None:
        """Fetch schedule when entity is added."""
        await super().async_added_to_hass()
        await self._fetch_schedule()

    async def async_set_value(self, value: str) -> None:
        """Set the alarm schedule from JSON."""
        try:
            schedule_data = json.loads(value)

            # Validate the structure
            if not isinstance(schedule_data, dict):
                _LOGGER.error("Schedule must be a JSON object")
                return

            # Validate days
            for day in schedule_data.keys():
                if day not in DAYS_OF_WEEK:
                    _LOGGER.error("Invalid day: %s. Must be one of: %s", day, DAYS_OF_WEEK)
                    return

            # Update the schedule via API
            success = await self.coordinator.client.update_alarm_schedule(self._side, schedule_data)

            if success:
                self._cached_schedule = schedule_data
                self.async_write_ha_state()
                _LOGGER.info("Alarm schedule updated for %s side", self._side)
            else:
                _LOGGER.error("Failed to update alarm schedule")

        except json.JSONDecodeError as err:
            _LOGGER.error("Invalid JSON: %s", err)
        except Exception as err:
            _LOGGER.error("Error setting schedule: %s", err)

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
