import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Use the string "temperature" directly for the device class.
DEVICE_CLASS_TEMPERATURE = "temperature"

SENSOR_TYPES = {
    "current_temp_f": {
        "name": "Current Temperature",
        "unit": "°F",
        "json_key": "currentTemperatureF",
        "device_class": DEVICE_CLASS_TEMPERATURE,
        "binary": False,
    },
    "target_temp_f": {
        "name": "Target Temperature",
        "unit": "°F",
        "json_key": "targetTemperatureF",
        "device_class": DEVICE_CLASS_TEMPERATURE,
        "binary": False,
    },
    "seconds_remaining": {
        "name": "Seconds Remaining",
        "unit": "s",
        "json_key": "secondsRemaining",
        "binary": False,
    },
    "is_alarm_vibrating": {
        "name": "Alarm Active",
        "unit": None,
        "json_key": "isAlarmVibrating",
        "binary": True,
    },
    "is_on": {
        "name": "Side On",
        "unit": None,
        "json_key": "isOn",
        "binary": True,
    },
    # Hub attributes as binary sensors:
    "is_priming": {
        "name": "Is Priming",
        "unit": None,
        "json_key": "isPriming",
        "binary": True,
    },
    "water_level": {
        "name": "Water Level",
        "unit": None,
        "json_key": "waterLevel",
        "binary": True,
    },
}

# Define which attributes are used for the left, right, and hub sides.
LEFT_ATTRIBUTES = ("current_temp_f", "target_temp_f", "seconds_remaining", "is_alarm_vibrating", "is_on")
RIGHT_ATTRIBUTES = LEFT_ATTRIBUTES  # same set as left
HUB_ATTRIBUTES = ("is_priming", "water_level")

async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up Eight Sleep sensors."""
    # Get coordinator from hass.data (created in __init__.py)
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]

    def create_entity(side, attr_key):
        sensor_info = SENSOR_TYPES[attr_key]
        if sensor_info.get("binary"):
            return EightSleepBinarySensor(coordinator, side=side, attribute_key=attr_key)
        return EightSleepSensor(coordinator, side=side, attribute_key=attr_key)

    left_entities = [
        create_entity("left", attr_key)
        for attr_key in LEFT_ATTRIBUTES
        if attr_key in SENSOR_TYPES
    ]
    right_entities = [
        create_entity("right", attr_key)
        for attr_key in RIGHT_ATTRIBUTES
        if attr_key in SENSOR_TYPES
    ]
    hub_entities = [
        create_entity("hub", attr_key)
        for attr_key in HUB_ATTRIBUTES
        if attr_key in SENSOR_TYPES
    ]

    async_add_entities(left_entities + right_entities + hub_entities)


class EightSleepSensor(CoordinatorEntity, SensorEntity):
    """
    Regular sensor entity for non-binary attributes (e.g. temperature, seconds remaining).
    """
    def __init__(self, coordinator, side: str, attribute_key: str):
        super().__init__(coordinator)
        self.side = side
        self.attribute_key = attribute_key

        sensor_info = SENSOR_TYPES[self.attribute_key]
        friendly_name = sensor_info["name"]
        unit = sensor_info["unit"]

        self._attr_name = f"Eight Sleep {side.capitalize()} {friendly_name}"
        self._attr_unique_id = f"eight_sleep_{side}_{attribute_key}"
        self._attr_native_unit_of_measurement = unit

        if sensor_info.get("device_class"):
            self._attr_device_class = sensor_info.get("device_class")

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        sensor_info = SENSOR_TYPES[self.attribute_key]
        json_key = sensor_info.get("json_key")
        if self.side in ("left", "right"):
            side_data = data.get(self.side, {})
            return side_data.get(json_key)
        elif self.side == "hub":
            return data.get(json_key)
        return None

    @property
    def device_info(self):
        host = self.coordinator.client._host
        port = self.coordinator.client._port
        return {
            "identifiers": {(DOMAIN, f"eight_sleep_{self.side}_device_{host}_{port}")},
            "name": f"Eight Sleep – {self.side.capitalize()}",
            "manufacturer": "Eight Sleep (Local)",
            "model": "Pod vLocal",
        }

class EightSleepBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """
    Binary sensor entity for boolean attributes (e.g. Alarm Vibrating, Device On, Is Priming, Water Level).
    """
    def __init__(self, coordinator, side: str, attribute_key: str):
        super().__init__(coordinator)
        self.side = side
        self.attribute_key = attribute_key

        sensor_info = SENSOR_TYPES[self.attribute_key]
        friendly_name = sensor_info["name"]

        self._attr_name = f"{friendly_name}"
        self._attr_unique_id = f"eight_sleep_{side}_{attribute_key}"
        # Optionally set a device class for binary sensors if needed.
        if sensor_info.get("device_class"):
            self._attr_device_class = sensor_info.get("device_class")

    @property
    def is_on(self):
        data = self.coordinator.data or {}
        sensor_info = SENSOR_TYPES[self.attribute_key]
        json_key = sensor_info.get("json_key")
        if self.side in ("left", "right"):
            side_data = data.get(self.side, {})
            value = side_data.get(json_key)
        elif self.side == "hub":
            value = data.get(json_key)
        return bool(value)

    @property
    def device_info(self):
        host = self.coordinator.client._host
        port = self.coordinator.client._port
        return {
            "identifiers": {(DOMAIN, f"eight_sleep_{self.side}_device_{host}_{port}")},
            "name": f"Eight Sleep – {self.side.capitalize()}",
            "manufacturer": "Eight Sleep (Local)",
            "model": "Pod vLocal",
        }
