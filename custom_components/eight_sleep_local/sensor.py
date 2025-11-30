import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    "current_temp_f": {
        "name": "Current Temperature",
        "unit": UnitOfTemperature.FAHRENHEIT,
        "json_key": "currentTemperatureF",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "binary": False,
    },
    "target_temp_f": {
        "name": "Target Temperature",
        "unit": UnitOfTemperature.FAHRENHEIT,
        "json_key": "targetTemperatureF",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
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

# Diagnostic sensors (hub-level info)
DIAGNOSTIC_SENSOR_TYPES = {
    "wifi_strength": {
        "name": "WiFi Signal",
        "unit": "dBm",
        "json_key": "wifiStrength",
        "icon": "mdi:wifi",
    },
    "hub_version": {
        "name": "Hub Version",
        "unit": None,
        "json_key": "hubVersion",
        "icon": "mdi:chip",
    },
    "cover_version": {
        "name": "Cover Version",
        "unit": None,
        "json_key": "coverVersion",
        "icon": "mdi:bed",
    },
    "freesleep_version": {
        "name": "Free-Sleep Version",
        "unit": None,
        "json_key": "freeSleep.version",
        "icon": "mdi:tag",
    },
    "freesleep_branch": {
        "name": "Free-Sleep Branch",
        "unit": None,
        "json_key": "freeSleep.branch",
        "icon": "mdi:source-branch",
    },
}

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

    # Add diagnostic sensors (hub-level)
    diagnostic_entities = [
        EightSleepDiagnosticSensor(coordinator, sensor_key)
        for sensor_key in DIAGNOSTIC_SENSOR_TYPES
    ]

    async_add_entities(left_entities + right_entities + hub_entities + diagnostic_entities)

    # Add health metrics sensors
    health_coordinator = entry_data.get("health_coordinator")
    if health_coordinator:
        health_entities = [
            # Left side health sensors
            EightSleepHeartRateSensor(health_coordinator, entry.entry_id, "left"),
            EightSleepHeartRateMinSensor(health_coordinator, entry.entry_id, "left"),
            EightSleepHeartRateMaxSensor(health_coordinator, entry.entry_id, "left"),
            EightSleepHRVSensor(health_coordinator, entry.entry_id, "left"),
            EightSleepBreathingRateSensor(health_coordinator, entry.entry_id, "left"),
            EightSleepSleepDurationSensor(health_coordinator, entry.entry_id, "left"),
            EightSleepTimesOutOfBedSensor(health_coordinator, entry.entry_id, "left"),
            # Right side health sensors
            EightSleepHeartRateSensor(health_coordinator, entry.entry_id, "right"),
            EightSleepHeartRateMinSensor(health_coordinator, entry.entry_id, "right"),
            EightSleepHeartRateMaxSensor(health_coordinator, entry.entry_id, "right"),
            EightSleepHRVSensor(health_coordinator, entry.entry_id, "right"),
            EightSleepBreathingRateSensor(health_coordinator, entry.entry_id, "right"),
            EightSleepSleepDurationSensor(health_coordinator, entry.entry_id, "right"),
            EightSleepTimesOutOfBedSensor(health_coordinator, entry.entry_id, "right"),
        ]
        async_add_entities(health_entities)


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
        if sensor_info.get("state_class"):
            self._attr_state_class = sensor_info.get("state_class")

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
        if sensor_info.get("state_class"):
            self._attr_state_class = sensor_info.get("state_class")

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
        # Handle string 'true'/'false' (e.g., waterLevel) as well as actual booleans
        if isinstance(value, str):
            return value.lower() == 'true'
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


# =============================================================================
# Health Metrics Sensors
# =============================================================================

class EightSleepHealthBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for health metrics sensors."""

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the health sensor."""
        super().__init__(coordinator)
        self._side = side
        self._entry_id = entry_id

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

    def _get_vitals_summary(self) -> dict | None:
        """Get vitals summary for this side."""
        data = self.coordinator.data or {}
        side_data = data.get(self._side, {})
        return side_data.get("vitals_summary")

    def _get_sleep_record(self) -> dict | None:
        """Get sleep record for this side."""
        data = self.coordinator.data or {}
        side_data = data.get(self._side, {})
        return side_data.get("sleep")


class EightSleepHeartRateSensor(EightSleepHealthBaseSensor):
    """Sensor for average heart rate (last night)."""

    _attr_icon = "mdi:heart-pulse"
    _attr_native_unit_of_measurement = "bpm"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, side)
        self._attr_name = f"Eight Sleep {side.capitalize()} Heart Rate"
        self._attr_unique_id = f"eight_sleep_{side}_heart_rate"

    @property
    def native_value(self) -> int | None:
        """Return average heart rate."""
        summary = self._get_vitals_summary()
        if summary:
            return summary.get("avgHeartRate")
        return None


class EightSleepHeartRateMinSensor(EightSleepHealthBaseSensor):
    """Sensor for minimum heart rate (last night)."""

    _attr_icon = "mdi:heart-minus"
    _attr_native_unit_of_measurement = "bpm"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, side)
        self._attr_name = f"Eight Sleep {side.capitalize()} Heart Rate Min"
        self._attr_unique_id = f"eight_sleep_{side}_heart_rate_min"

    @property
    def native_value(self) -> int | None:
        """Return minimum heart rate."""
        summary = self._get_vitals_summary()
        if summary:
            return summary.get("minHeartRate")
        return None


class EightSleepHeartRateMaxSensor(EightSleepHealthBaseSensor):
    """Sensor for maximum heart rate (last night)."""

    _attr_icon = "mdi:heart-plus"
    _attr_native_unit_of_measurement = "bpm"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, side)
        self._attr_name = f"Eight Sleep {side.capitalize()} Heart Rate Max"
        self._attr_unique_id = f"eight_sleep_{side}_heart_rate_max"

    @property
    def native_value(self) -> int | None:
        """Return maximum heart rate."""
        summary = self._get_vitals_summary()
        if summary:
            return summary.get("maxHeartRate")
        return None


class EightSleepHRVSensor(EightSleepHealthBaseSensor):
    """Sensor for average HRV (last night)."""

    _attr_icon = "mdi:wave"
    _attr_native_unit_of_measurement = "ms"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, side)
        self._attr_name = f"Eight Sleep {side.capitalize()} HRV"
        self._attr_unique_id = f"eight_sleep_{side}_hrv"

    @property
    def native_value(self) -> int | None:
        """Return average HRV."""
        summary = self._get_vitals_summary()
        if summary:
            return summary.get("avgHRV")
        return None


class EightSleepBreathingRateSensor(EightSleepHealthBaseSensor):
    """Sensor for average breathing rate (last night)."""

    _attr_icon = "mdi:lungs"
    _attr_native_unit_of_measurement = "/min"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, side)
        self._attr_name = f"Eight Sleep {side.capitalize()} Breathing Rate"
        self._attr_unique_id = f"eight_sleep_{side}_breathing_rate"

    @property
    def native_value(self) -> int | None:
        """Return average breathing rate."""
        summary = self._get_vitals_summary()
        if summary:
            return summary.get("avgBreathingRate")
        return None


class EightSleepSleepDurationSensor(EightSleepHealthBaseSensor):
    """Sensor for sleep duration (last night)."""

    _attr_icon = "mdi:clock-outline"
    _attr_native_unit_of_measurement = "h"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, side)
        self._attr_name = f"Eight Sleep {side.capitalize()} Sleep Duration"
        self._attr_unique_id = f"eight_sleep_{side}_sleep_duration"

    @property
    def native_value(self) -> float | None:
        """Return sleep duration in hours."""
        sleep = self._get_sleep_record()
        if sleep:
            seconds = sleep.get("sleep_period_seconds", 0)
            if seconds:
                return round(seconds / 3600, 1)
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional sleep attributes."""
        sleep = self._get_sleep_record()
        if sleep:
            return {
                "entered_bed_at": sleep.get("entered_bed_at"),
                "left_bed_at": sleep.get("left_bed_at"),
                "sleep_period_seconds": sleep.get("sleep_period_seconds"),
            }
        return {}


class EightSleepTimesOutOfBedSensor(EightSleepHealthBaseSensor):
    """Sensor for times out of bed (last night)."""

    _attr_icon = "mdi:bed-empty"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry_id: str, side: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id, side)
        self._attr_name = f"Eight Sleep {side.capitalize()} Times Out of Bed"
        self._attr_unique_id = f"eight_sleep_{side}_times_out_of_bed"

    @property
    def native_value(self) -> int | None:
        """Return times exited bed."""
        sleep = self._get_sleep_record()
        if sleep:
            return sleep.get("times_exited_bed", 0)
        return None


# =============================================================================
# Diagnostic Sensors
# =============================================================================

class EightSleepDiagnosticSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor for hub-level info (WiFi, versions, etc.)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, sensor_key: str) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator)
        self._sensor_key = sensor_key
        sensor_info = DIAGNOSTIC_SENSOR_TYPES[sensor_key]

        self._attr_name = f"Eight Sleep {sensor_info['name']}"
        self._attr_unique_id = f"eight_sleep_hub_{sensor_key}"
        self._attr_native_unit_of_measurement = sensor_info.get("unit")
        self._attr_icon = sensor_info.get("icon")

    @property
    def native_value(self):
        """Return the sensor value."""
        data = self.coordinator.data or {}
        json_key = DIAGNOSTIC_SENSOR_TYPES[self._sensor_key]["json_key"]

        # Handle nested keys like "freeSleep.version"
        if "." in json_key:
            parts = json_key.split(".")
            value = data
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value
        return data.get(json_key)

    @property
    def device_info(self):
        """Return device info - associate with Hub device."""
        host = self.coordinator.client._host
        port = self.coordinator.client._port
        return {
            "identifiers": {(DOMAIN, f"eight_sleep_hub_device_{host}_{port}")},
            "name": "Eight Sleep – Hub",
            "manufacturer": "Eight Sleep (Local)",
            "model": "Pod vLocal",
        }
