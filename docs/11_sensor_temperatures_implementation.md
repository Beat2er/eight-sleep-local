# 11 - Sensor Temperatures Implementation

This document outlines the implementation plan for exposing raw sensor temperature data (ambient, heatsink, etc.) from the biometrics stream.

---

## Overview

### Background

The Eight Sleep Pod captures detailed temperature readings from multiple sensors via the biometrics stream:
- **frzTemp** (freeze temps): ambient, heatsink, left/right side temps
- **bedTemp**: ambient, MCU, heater unit, detailed bed zone temps

Currently, only `currentTemperatureF` is exposed (converted from heat level -100 to 100), but the raw sensor readings provide more detailed information.

### Features to Implement

1. **Sensor Temperature Data** - Read from biometrics stream
   - Ambient temperature (room/environment)
   - Heatsink temperature (cooling system)
   - Left/right bed surface temperatures

2. **API Exposure** - Add to `/api/deviceStatus`
   - Optional `sensorTemps` field (null when biometrics disabled)
   - Temperature values in raw units (need conversion factor)

3. **HA Integration** - New sensor entities
   - Ambient temperature sensor
   - Heatsink temperature sensor (diagnostic)
   - Bed surface temperature sensors per side

### Important Constraint

Sensor temperatures are **only available when biometrics stream is enabled**. The implementation must handle the case where biometrics is disabled gracefully.

---

## Raw Data Format

### frzTemp Record (from biometrics stream)

```python
class FrzTempData(TypedDict):
    type: str      # "frzTemp"
    ts: int        # epoch timestamp
    left: int      # left side temp (raw units)
    right: int     # right side temp (raw units)
    amb: int       # ambient temperature (raw units)
    hs: int        # heatsink temperature (raw units)
    seq: int       # sequence number
```

Example:
```json
{
    "amb": 2168,
    "hs": 3168,
    "left": 1975,
    "right": 1981,
    "seq": 1610686,
    "ts": 1736506828,
    "type": "frzTemp"
}
```

### Temperature Conversion

Raw values appear to be in centi-degrees (divide by 100 for actual temp):
- `amb: 2168` -> 21.68°C (70.9°F) - reasonable room temp
- `hs: 3168` -> 31.68°C (89.0°F) - heatsink runs warmer

---

## Phase 1: Update Biometrics Stream

### Step 1.1: Modify stream.py to Capture frzTemp

Update `free-sleep/biometrics/stream/stream.py` to also process `frzTemp` records:

```python
# In follow_latest_file method, after decoding:
if decoded_data['type'] == 'frzTemp':
    update_sensor_temps(decoded_data)
    continue

if decoded_data['type'] != 'piezo-dual':
    continue
```

### Step 1.2: Add service_health.py Function

Add to `free-sleep/biometrics/service_health.py`:

```python
def update_sensor_temps(frz_temp_data: dict) -> None:
    """Update sensor temperatures in services DB."""
    try:
        services_path = '/home/dac/free-sleep/server/data/services.json'
        with open(services_path, 'r') as f:
            data = json.load(f)

        data['biometrics']['sensorTemps'] = {
            'ambient': frz_temp_data.get('amb'),
            'heatsink': frz_temp_data.get('hs'),
            'left': frz_temp_data.get('left'),
            'right': frz_temp_data.get('right'),
            'lastUpdated': datetime.now().isoformat(),
        }

        with open(services_path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f'Failed to update sensor temps: {e}')
```

---

## Phase 2: Update Server Schema & API

### Step 2.1: Update servicesSchema.ts

Add to `free-sleep/server/src/db/servicesSchema.ts`:

```typescript
export const SensorTempsSchema = z.object({
  ambient: z.number().nullable(),
  heatsink: z.number().nullable(),
  left: z.number().nullable(),
  right: z.number().nullable(),
  lastUpdated: z.string().nullable(),
});

export type SensorTemps = z.infer<typeof SensorTempsSchema>;

// Update ServicesSchema to include:
export const ServicesSchema = z.object({
  biometrics: z.object({
    enabled: z.boolean(),
    jobs: z.object({...}),
    presence: PresenceSchema.optional(),
    sensorTemps: SensorTempsSchema.optional(),  // NEW
  }),
  // ...
});
```

### Step 2.2: Update deviceStatusSchema.ts

Add optional sensorTemps to DeviceStatusSchema:

```typescript
export const DeviceStatusSchema = z.object({
  // ... existing fields ...
  sensorTemps: z.object({
    ambientC: z.number().nullable(),
    ambientF: z.number().nullable(),
    heatsinkC: z.number().nullable(),
    leftC: z.number().nullable(),
    rightC: z.number().nullable(),
    lastUpdated: z.string().nullable(),
  }).optional().nullable(),
});
```

### Step 2.3: Update loadDeviceStatus.ts

In `loadDeviceStatus()`, read sensor temps from services DB:

```typescript
// Read sensor temps from services if biometrics enabled
let sensorTemps = null;
try {
  await servicesDB.read();
  const rawTemps = servicesDB.data?.biometrics?.sensorTemps;
  if (rawTemps && rawTemps.ambient !== null) {
    // Convert from raw units (centi-degrees C) to C and F
    const toC = (raw: number | null) => raw !== null ? raw / 100 : null;
    const toF = (c: number | null) => c !== null ? Math.round(c * 9/5 + 32) : null;

    const ambientC = toC(rawTemps.ambient);
    sensorTemps = {
      ambientC,
      ambientF: toF(ambientC),
      heatsinkC: toC(rawTemps.heatsink),
      leftC: toC(rawTemps.left),
      rightC: toC(rawTemps.right),
      lastUpdated: rawTemps.lastUpdated,
    };
  }
} catch (e) {
  logger.debug('Sensor temps not available');
}

const deviceStatus: DeviceStatus = {
  // ... existing fields ...
  sensorTemps,
};
```

---

## Phase 3: Update Mock Server

### Step 3.1: Add Mock Sensor Temps

Update `free-sleep/server/src/routes/deviceStatus/deviceStatus.ts`:

```typescript
let MOCK_DEVICE_STATUS = {
  // ... existing fields ...
  sensorTemps: {
    ambientC: 21.5,
    ambientF: 71,
    heatsinkC: 31.0,
    leftC: 28.5,
    rightC: 29.0,
    lastUpdated: new Date().toISOString(),
  },
};
```

---

## Phase 4: HA Integration

### Step 4.1: Add Sensor Types

Update `sensor.py` DIAGNOSTIC_SENSOR_TYPES:

```python
SENSOR_TEMP_TYPES = {
    "ambient_temp": {
        "name": "Ambient Temperature",
        "json_key": "sensorTemps.ambientF",
        "unit": UnitOfTemperature.FAHRENHEIT,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:thermometer",
    },
    "heatsink_temp": {
        "name": "Heatsink Temperature",
        "json_key": "sensorTemps.heatsinkC",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:thermometer-alert",
        "entity_category": "diagnostic",
    },
}

# Per-side sensor temps (optional)
SIDE_SENSOR_TEMP_TYPES = {
    "bed_surface_temp": {
        "name": "Bed Surface Temperature",
        "json_key_template": "sensorTemps.{side}C",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:bed-clock",
    },
}
```

### Step 4.2: Create EightSleepSensorTempSensor Class

```python
class EightSleepSensorTempSensor(CoordinatorEntity, SensorEntity):
    """Sensor for raw temperature readings from biometrics stream."""

    def __init__(self, coordinator, sensor_key: str) -> None:
        super().__init__(coordinator)
        self._sensor_key = sensor_key
        sensor_info = SENSOR_TEMP_TYPES[sensor_key]

        self._attr_name = f"Eight Sleep {sensor_info['name']}"
        self._attr_unique_id = f"eight_sleep_hub_{sensor_key}"
        self._attr_native_unit_of_measurement = sensor_info.get("unit")
        self._attr_device_class = sensor_info.get("device_class")
        self._attr_state_class = sensor_info.get("state_class")
        self._attr_icon = sensor_info.get("icon")

        if sensor_info.get("entity_category") == "diagnostic":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        json_key = SENSOR_TEMP_TYPES[self._sensor_key]["json_key"]

        # Handle nested keys like "sensorTemps.ambientF"
        parts = json_key.split(".")
        value = data
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    @property
    def available(self) -> bool:
        """Return True if sensor temps data is available."""
        data = self.coordinator.data or {}
        sensor_temps = data.get("sensorTemps")
        return sensor_temps is not None

    @property
    def device_info(self):
        host = self.coordinator.client._host
        port = self.coordinator.client._port
        return {
            "identifiers": {(DOMAIN, f"eight_sleep_hub_device_{host}_{port}")},
            "name": "Eight Sleep - Hub",
            "manufacturer": "Eight Sleep (Local)",
            "model": "Pod vLocal",
        }
```

---

## File Changes Summary

| File | Action | Purpose |
|------|--------|---------|
| `free-sleep/biometrics/stream/stream.py` | Modify | Capture frzTemp records |
| `free-sleep/biometrics/service_health.py` | Modify | Add update_sensor_temps() |
| `free-sleep/server/src/db/servicesSchema.ts` | Modify | Add SensorTempsSchema |
| `free-sleep/server/src/routes/deviceStatus/deviceStatusSchema.ts` | Modify | Add sensorTemps to schema |
| `free-sleep/server/src/8sleep/loadDeviceStatus.ts` | Modify | Read & convert sensor temps |
| `free-sleep/server/src/routes/deviceStatus/deviceStatus.ts` | Modify | Add mock sensor temps |
| `eight-sleep-local/.../sensor.py` | Modify | Add sensor temp entities |

---

## New Entities

### Hub Device Sensors
- `sensor.eight_sleep_ambient_temperature` - Room temperature (°F, auto-converts)
- `sensor.eight_sleep_heatsink_temperature` - Cooling system temp (°C, diagnostic)

### Per-Side Sensors (Optional)
- `sensor.eight_sleep_left_bed_surface_temperature` - Left bed surface (°C)
- `sensor.eight_sleep_right_bed_surface_temperature` - Right bed surface (°C)

---

## Testing Checklist

- [ ] Mock server returns sensorTemps data
- [ ] Biometrics stream captures frzTemp and updates servicesDB
- [ ] deviceStatus API returns sensorTemps (null when biometrics disabled)
- [ ] HA sensors show values when available
- [ ] HA sensors show unavailable when biometrics disabled
- [ ] Temperature unit conversion works correctly (C to F in HA)

---

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Plan document | Done | This file |
| Biometrics stream update | Done | stream.py captures frzTemp |
| service_health.py | Done | update_sensor_temps() added |
| servicesDB schema | Done | SensorTempsSchema added |
| deviceStatus API | Done | Reads from servicesDB, converts temps |
| Mock server | Done | Mock sensorTemps added |
| HA integration | Done | EightSleepSensorTempSensor class |
