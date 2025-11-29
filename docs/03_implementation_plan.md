# 03 - Implementation Plan

This document outlines the step-by-step implementation plan for adding new features to eight-sleep-local.

---

## Phase 1: API Client Enhancement (`localEight/device.py`)

### Step 1.1: Add POST Methods to LocalEightSleep

Add the following methods to the `LocalEightSleep` class:

```python
async def set_temperature(self, side: str, temperature_f: int, duration: int = None) -> bool:
    """Set target temperature for a side (55-110°F)."""
    payload = {
        side: {
            "targetTemperatureF": temperature_f
        }
    }
    if duration is not None:
        payload[side]["secondsRemaining"] = duration
    return await self.api_request("POST", "/api/deviceStatus", payload)

async def turn_on(self, side: str, duration: int = 43200) -> bool:
    """Turn on a bed side (default 12 hours)."""
    payload = {
        side: {
            "isOn": True,
            "secondsRemaining": duration
        }
    }
    return await self.api_request("POST", "/api/deviceStatus", payload)

async def turn_off(self, side: str) -> bool:
    """Turn off a bed side."""
    payload = {
        side: {
            "isOn": False
        }
    }
    return await self.api_request("POST", "/api/deviceStatus", payload)

async def stop_alarm(self, side: str) -> bool:
    """Stop/clear an active alarm."""
    payload = {
        side: {
            "isAlarmVibrating": False
        }
    }
    return await self.api_request("POST", "/api/deviceStatus", payload)

async def start_priming(self) -> bool:
    """Start the pod priming process."""
    payload = {
        "isPriming": True
    }
    return await self.api_request("POST", "/api/deviceStatus", payload)

async def trigger_alarm(
    self,
    side: str,
    intensity: int = 80,
    pattern: str = "rise",
    duration: int = 60
) -> bool:
    """Trigger alarm vibration on a side."""
    payload = {
        "side": side,
        "vibrationIntensity": intensity,
        "vibrationPattern": pattern,
        "duration": duration
    }
    return await self.api_request("POST", "/api/alarm", payload)
```

### Step 1.2: Improve api_request Return Value

Update `api_request` to return proper success/failure indication:

```python
async def api_request(
    self,
    method: str,
    api_slug: str,
    data: dict[str, Any]
) -> bool | dict:
    """Make API request. Returns response JSON or True for 204, False on error."""
    assert self._api_session is not None, "Session not initialized. Call `start()` first."
    url = f"http://{self._host}:{self._port}{api_slug}"
    try:
        async with self._api_session.request(method=method, url=url, json=data) as resp:
            if resp.status == 204:
                return True
            if resp.status == 200:
                return await resp.json()
            _LOGGER.error(f"Received unexpected status code: {resp.status}")
            return False
    except (ClientError, asyncio.TimeoutError, ConnectionRefusedError) as err:
        _LOGGER.error(f"Error in API request: {err}")
        return False
```

---

## Phase 2: Platform Extensions

### Step 2.1: Add Switch Platform (`switch.py`)

Create `custom_components/eight_sleep_local/switch.py`:

**Purpose**: Provide on/off toggle for each bed side

**Entities**:
- `switch.eight_sleep_left_power`
- `switch.eight_sleep_right_power`

**Key Implementation**:
```python
class EightSleepSwitch(CoordinatorEntity, SwitchEntity):
    async def async_turn_on(self, **kwargs):
        await self.coordinator.client.turn_on(self.side)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.client.turn_off(self.side)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self):
        return self.coordinator.data.get(self.side, {}).get("isOn", False)
```

### Step 2.2: Add Number Platform (`number.py`)

Create `custom_components/eight_sleep_local/number.py`:

**Purpose**: Provide temperature adjustment slider for each side

**Entities**:
- `number.eight_sleep_left_temperature`
- `number.eight_sleep_right_temperature`

**Key Implementation**:
```python
class EightSleepTemperature(CoordinatorEntity, NumberEntity):
    _attr_native_min_value = 55
    _attr_native_max_value = 110
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "°F"

    async def async_set_native_value(self, value: float):
        await self.coordinator.client.set_temperature(self.side, int(value))
        await self.coordinator.async_request_refresh()

    @property
    def native_value(self):
        return self.coordinator.data.get(self.side, {}).get("targetTemperatureF")
```

### Step 2.3: Add Button Platform (`button.py`)

Create `custom_components/eight_sleep_local/button.py`:

**Purpose**: One-shot actions (prime, stop alarm)

**Entities**:
- `button.eight_sleep_prime_pod`
- `button.eight_sleep_left_stop_alarm`
- `button.eight_sleep_right_stop_alarm`

**Key Implementation**:
```python
class EightSleepPrimeButton(CoordinatorEntity, ButtonEntity):
    async def async_press(self):
        await self.coordinator.client.start_priming()

class EightSleepStopAlarmButton(CoordinatorEntity, ButtonEntity):
    async def async_press(self):
        await self.coordinator.client.stop_alarm(self.side)
        await self.coordinator.async_request_refresh()
```

---

## Phase 3: Service Registration

### Step 3.1: Create services.yaml

Create `custom_components/eight_sleep_local/services.yaml` with service definitions (see 02_new_required_features.md).

### Step 3.2: Register Services in __init__.py

Update `__init__.py`:

```python
PLATFORMS = ["sensor", "switch", "number", "button"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # ... existing setup ...

    # Register services
    async def handle_heat_set(call):
        entity_id = call.data.get("entity_id")
        target = call.data.get("target")
        duration = call.data.get("duration")
        # Get client from coordinator, call set_temperature

    hass.services.async_register(
        DOMAIN, "heat_set", handle_heat_set, schema=HEAT_SET_SCHEMA
    )
    # ... register other services ...
```

### Step 3.3: Update manifest.json

Add aiohttp requirement if not present:
```json
{
  "requirements": ["aiohttp>=3.8.0"]
}
```

---

## Phase 4: Testing & Validation

### Step 4.1: Manual Testing Checklist

- [ ] Set temperature via number entity slider
- [ ] Turn side on/off via switch entity
- [ ] Stop alarm via button entity
- [ ] Prime pod via button entity
- [ ] Verify sensor updates after actions
- [ ] Test with both left and right sides

### Step 4.2: Edge Cases

- [ ] Handle API timeouts gracefully
- [ ] Handle invalid temperature values (out of range)
- [ ] Handle action when side is already in desired state
- [ ] Verify coordinator refresh after actions

---

## File Changes Summary

| File | Action | Purpose |
|------|--------|---------|
| `localEight/device.py` | Modify | Add POST methods |
| `__init__.py` | Modify | Add platforms, register services |
| `switch.py` | Create | Power on/off control |
| `number.py` | Create | Temperature control |
| `button.py` | Create | Prime, stop alarm |
| `services.yaml` | Create | Service definitions |
| `manifest.json` | Modify | Add requirements |
| `const.py` | Modify | Add new constants |

---

## Implementation Order

1. **Phase 1.1**: Add POST methods to device.py
2. **Phase 1.2**: Update api_request for proper return handling
3. **Phase 2.1**: Create switch.py for on/off
4. **Phase 2.2**: Create number.py for temperature
5. **Phase 2.3**: Create button.py for actions
6. **Phase 3.1**: Create services.yaml
7. **Phase 3.2**: Update __init__.py (platforms + services)
8. **Phase 4**: Testing

---

## Alternative: Climate Entity Approach

Instead of separate switch + number entities, a `climate` platform could provide a more integrated experience:

**Pros**:
- Single entity per side
- Native thermostat UI in Home Assistant
- HVAC modes for on/off

**Cons**:
- More complex implementation
- May not map perfectly to Eight Sleep's model

**Decision**: Start with switch + number approach for simplicity. Climate entity can be added as enhancement later.

---

## Notes

- The coordinator pattern is already in place (sensor.py) - reuse it
- All new entities should inherit from `CoordinatorEntity`
- Always call `coordinator.async_request_refresh()` after state-changing actions
- Services are optional if entities provide the same functionality, but useful for automations
