# 10 - Diagnostics, LED Brightness & Events Implementation

This document outlines the implementation plan for adding diagnostic sensors, LED brightness control, and HA events.

---

## Overview

### Features to Implement

1. **Diagnostic Sensors** - Read-only info from `/api/deviceStatus`
   - WiFi signal strength
   - Hub version (Pod 3/4/5)
   - Cover version (Pod 3/4/5)
   - Free-sleep version
   - Free-sleep branch

2. **LED Brightness Control** - Number entity (0-100)
   - Read from `settings.ledBrightness`
   - Write via POST to `/api/deviceStatus`

3. **HA Events** - Fire events on state changes
   - `eight_sleep_bed_entry` - When presence goes false → true
   - `eight_sleep_bed_exit` - When presence goes true → false
   - `eight_sleep_alarm_triggered` - When alarm starts vibrating

---

## Phase 1: Update Mock Server

### Step 1.1: Add Missing Fields to Mock

Update `free-sleep/server/src/routes/deviceStatus/deviceStatus.ts`:

```typescript
const MOCK_DEVICE_STATUS = {
  left: {
    currentTemperatureLevel: 0,
    currentTemperatureF: 75,
    targetTemperatureF: 80,
    secondsRemaining: 3600,
    isAlarmVibrating: false,
    isOn: true,
  },
  right: {
    currentTemperatureLevel: -10,
    currentTemperatureF: 72,
    targetTemperatureF: 78,
    secondsRemaining: 3600,
    isAlarmVibrating: false,
    isOn: true,
  },
  waterLevel: 'true',
  isPriming: false,
  sensorLabel: 'mock-device-local-dev',
  // NEW: Add diagnostic fields
  wifiStrength: -45,
  hubVersion: 'Pod 4',
  coverVersion: 'Pod 4',
  freeSleep: {
    version: '1.0.0-mock',
    branch: 'main',
  },
  settings: {
    v: 1,
    gainLeft: 100,
    gainRight: 100,
    ledBrightness: 50,
  },
};
```

---

## Phase 2: Add Diagnostic Sensors

### Step 2.1: Update sensor.py

Add new sensor types for diagnostics:

```python
DIAGNOSTIC_SENSOR_TYPES = {
    "wifi_strength": {
        "name": "WiFi Signal",
        "unit": "dBm",
        "json_key": "wifiStrength",
        "icon": "mdi:wifi",
        "entity_category": "diagnostic",
    },
    "hub_version": {
        "name": "Hub Version",
        "unit": None,
        "json_key": "hubVersion",
        "icon": "mdi:chip",
        "entity_category": "diagnostic",
    },
    "cover_version": {
        "name": "Cover Version",
        "unit": None,
        "json_key": "coverVersion",
        "icon": "mdi:bed",
        "entity_category": "diagnostic",
    },
    "freesleep_version": {
        "name": "Free-Sleep Version",
        "unit": None,
        "json_key": "freeSleep.version",
        "icon": "mdi:tag",
        "entity_category": "diagnostic",
    },
    "freesleep_branch": {
        "name": "Free-Sleep Branch",
        "unit": None,
        "json_key": "freeSleep.branch",
        "icon": "mdi:source-branch",
        "entity_category": "diagnostic",
    },
}
```

### Step 2.2: Create EightSleepDiagnosticSensor Class

```python
class EightSleepDiagnosticSensor(CoordinatorEntity, SensorEntity):
    """Diagnostic sensor for hub-level info."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, sensor_key: str):
        super().__init__(coordinator)
        self._sensor_key = sensor_key
        sensor_info = DIAGNOSTIC_SENSOR_TYPES[sensor_key]

        self._attr_name = f"Eight Sleep {sensor_info['name']}"
        self._attr_unique_id = f"eight_sleep_hub_{sensor_key}"
        self._attr_native_unit_of_measurement = sensor_info.get("unit")
        self._attr_icon = sensor_info.get("icon")

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        json_key = DIAGNOSTIC_SENSOR_TYPES[self._sensor_key]["json_key"]

        # Handle nested keys like "freeSleep.version"
        if "." in json_key:
            parts = json_key.split(".")
            value = data
            for part in parts:
                value = value.get(part, {}) if isinstance(value, dict) else None
            return value
        return data.get(json_key)

    @property
    def device_info(self):
        # Associate with Hub device
        host = self.coordinator.client._host
        port = self.coordinator.client._port
        return {
            "identifiers": {(DOMAIN, f"eight_sleep_hub_device_{host}_{port}")},
            "name": "Eight Sleep – Hub",
            "manufacturer": "Eight Sleep (Local)",
            "model": "Pod vLocal",
        }
```

---

## Phase 3: Add LED Brightness Control

### Step 3.1: Add API Method to device.py

```python
async def set_led_brightness(self, brightness: int) -> bool:
    """Set LED brightness (0-100)."""
    payload = {
        "settings": {
            "ledBrightness": brightness
        }
    }
    return await self.api_request("POST", "/api/deviceStatus", payload)
```

### Step 3.2: Add to number.py

Add LED brightness number entity:

```python
class EightSleepLEDBrightness(CoordinatorEntity, NumberEntity):
    """Number entity for LED brightness control."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_icon = "mdi:led-on"
    _attr_name = "Eight Sleep LED Brightness"
    _attr_unique_id = "eight_sleep_hub_led_brightness"

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.set_led_brightness(int(value))
        await self.coordinator.async_request_refresh()

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data or {}
        settings = data.get("settings", {})
        return settings.get("ledBrightness")

    @property
    def device_info(self):
        # Associate with Hub device
        host = self.coordinator.client._host
        port = self.coordinator.client._port
        return {
            "identifiers": {(DOMAIN, f"eight_sleep_hub_device_{host}_{port}")},
            "name": "Eight Sleep – Hub",
            "manufacturer": "Eight Sleep (Local)",
            "model": "Pod vLocal",
        }
```

---

## Phase 4: Add HA Events

### Step 4.1: Track Previous State in Coordinator

Update `__init__.py` coordinator to track previous values:

```python
class EightSleepCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, client: LocalEightSleep) -> None:
        super().__init__(...)
        self.client = client
        self._previous_data: dict | None = None

    async def _async_update_data(self):
        data = await self.client.get_device_status()

        if self._previous_data is not None:
            self._check_and_fire_events(data)

        self._previous_data = data
        return data

    def _check_and_fire_events(self, new_data: dict) -> None:
        """Compare with previous data and fire events on changes."""
        for side in ("left", "right"):
            old_side = self._previous_data.get(side, {})
            new_side = new_data.get(side, {})

            # Check alarm state change
            old_alarm = old_side.get("isAlarmVibrating", False)
            new_alarm = new_side.get("isAlarmVibrating", False)
            if not old_alarm and new_alarm:
                self.hass.bus.async_fire(
                    "eight_sleep_alarm_triggered",
                    {"side": side}
                )
```

### Step 4.2: Track Presence Changes in Health Coordinator

```python
class EightSleepHealthCoordinator(DataUpdateCoordinator):
    def __init__(self, ...):
        ...
        self._previous_presence: dict = {"left": None, "right": None}

    async def _async_update_data(self):
        # ... existing fetch logic ...

        # Check presence changes
        presence_data = await self.client.get_presence()
        if presence_data:
            for side in ("left", "right"):
                side_presence = presence_data.get(side, {})
                current = side_presence.get("present")
                previous = self._previous_presence.get(side)

                if previous is not None and current != previous:
                    event_name = "eight_sleep_bed_entry" if current else "eight_sleep_bed_exit"
                    self.hass.bus.async_fire(event_name, {"side": side})

                self._previous_presence[side] = current

        return result
```

---

## Phase 5: Update Mock Server POST Handler

### Step 5.1: Handle settings in POST

Update `deviceStatus.ts` to handle settings updates in mock mode:

```typescript
router.post('/deviceStatus', async (req: Request, res: Response) => {
  // ... validation ...

  if (config.remoteDevMode) {
    logger.debug('Mock deviceStatus POST (remoteDevMode):', body);
    // Optionally update mock state for settings
    if (body.settings?.ledBrightness !== undefined) {
      MOCK_DEVICE_STATUS.settings.ledBrightness = body.settings.ledBrightness;
    }
    res.status(204).end();
    return;
  }
  // ... existing code ...
});
```

---

## File Changes Summary

| File | Action | Purpose |
|------|--------|---------|
| `free-sleep/server/.../deviceStatus.ts` | Modify | Add diagnostic fields to mock |
| `eight-sleep-local/.../sensor.py` | Modify | Add diagnostic sensors |
| `eight-sleep-local/.../number.py` | Modify | Add LED brightness control |
| `eight-sleep-local/.../device.py` | Modify | Add set_led_brightness method |
| `eight-sleep-local/.../__init__.py` | Modify | Add event firing logic |

---

## Implementation Order

1. **Phase 1**: Update mock server with diagnostic fields
2. **Phase 2**: Add diagnostic sensors to HA
3. **Phase 3**: Add LED brightness number entity
4. **Phase 4**: Add event firing for bed entry/exit and alarm
5. **Testing**: Verify in HA with mock server

---

## New Entities

### Diagnostic Sensors (Hub device)
- `sensor.eight_sleep_wifi_signal` - WiFi strength in dBm
- `sensor.eight_sleep_hub_version` - "Pod 3" / "Pod 4" / "Pod 5"
- `sensor.eight_sleep_cover_version` - "Pod 3" / "Pod 4" / "Pod 5"
- `sensor.eight_sleep_freesleep_version` - e.g., "1.0.0"
- `sensor.eight_sleep_freesleep_branch` - e.g., "main"

### Number Entity (Hub device)
- `number.eight_sleep_led_brightness` - 0-100 slider

### Events
- `eight_sleep_bed_entry` - data: `{"side": "left"|"right"}`
- `eight_sleep_bed_exit` - data: `{"side": "left"|"right"}`
- `eight_sleep_alarm_triggered` - data: `{"side": "left"|"right"}`

---

## Testing Checklist

- [ ] Mock server returns all diagnostic fields
- [ ] Diagnostic sensors show values in HA
- [ ] LED brightness slider works (read + write)
- [ ] Events fire on presence change (test with mock data changes)
- [ ] Events fire on alarm trigger

---

## Implementation Status

All features have been implemented:

| Feature | Status | Commit |
|---------|--------|--------|
| Mock server diagnostic fields | ✅ Done | `5a773b2` |
| Diagnostic sensors (sensor.py) | ✅ Done | `24484be` |
| LED brightness API (device.py) | ✅ Done | `24484be` |
| LED brightness number entity | ✅ Done | `24484be` |
| HA events (bed entry/exit, alarm) | ✅ Done | `89d960c` |

### Event Usage in Automations

```yaml
# Example automation for bed entry
automation:
  - alias: "Bed Entry - Turn off lights"
    trigger:
      - platform: event
        event_type: eight_sleep_bed_entry
        event_data:
          side: left
    action:
      - service: light.turn_off
        target:
          entity_id: light.bedroom

# Example automation for alarm triggered
automation:
  - alias: "Alarm - Turn on lights"
    trigger:
      - platform: event
        event_type: eight_sleep_alarm_triggered
    action:
      - service: light.turn_on
        target:
          entity_id: light.bedroom
        data:
          brightness_pct: 50
```
