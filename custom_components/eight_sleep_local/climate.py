"""Climate platform for Eight Sleep Local."""
import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .switch import SYNC_MODE_KEY

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Eight Sleep climate entities."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]

    entities = [
        EightSleepClimate(coordinator, entry.entry_id, "left"),
        EightSleepClimate(coordinator, entry.entry_id, "right"),
    ]

    async_add_entities(entities)


class EightSleepClimate(CoordinatorEntity, ClimateEntity):
    """Climate entity for Eight Sleep bed side temperature control."""

    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT_COOL]
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_min_temp = 55
    _attr_max_temp = 110
    _attr_target_temperature_step = 1
    _attr_icon = "mdi:bed-clock"

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._side = side
        self._entry_id = entry_id
        self._attr_name = f"Eight Sleep {side.capitalize()}"
        self._attr_unique_id = f"eight_sleep_{side}_climate"

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        data = self.coordinator.data or {}
        side_data = data.get(self._side, {})
        is_on = side_data.get("isOn", False)
        return HVACMode.HEAT_COOL if is_on else HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        data = self.coordinator.data or {}
        side_data = data.get(self._side, {})
        return side_data.get("currentTemperatureF")

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        data = self.coordinator.data or {}
        side_data = data.get(self._side, {})
        return side_data.get("targetTemperatureF")

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return

        temp = int(temperature)

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

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.client.turn_off_side(self._side)
        elif hvac_mode == HVACMode.HEAT_COOL:
            await self.coordinator.client.turn_on_side(self._side)

        await self.coordinator.async_request_refresh()

    @property
    def device_info(self):
        """Return device info."""
        host = self.coordinator.client._host
        port = self.coordinator.client._port
        return {
            "identifiers": {(DOMAIN, f"eight_sleep_{self._side}_device_{host}_{port}")},
            "name": f"Eight Sleep - {self._side.capitalize()}",
            "manufacturer": "Eight Sleep (Local)",
            "model": "Pod vLocal",
        }
