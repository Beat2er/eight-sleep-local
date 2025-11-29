# 04 - Feature Requirements

Final feature requirements agreed upon for implementation.

---

## Device Structure

Three Home Assistant devices (unchanged from current):

```
Eight Sleep – Left      (side-specific entities)
Eight Sleep – Right     (side-specific entities)
Eight Sleep – Hub       (pod-level entities + shared settings)
```

---

## Entities by Device

### Eight Sleep – Left

| Entity ID | Type | Description |
|-----------|------|-------------|
| `switch.eight_sleep_left_power` | switch | Turn side on/off |
| `number.eight_sleep_left_temperature` | number | Target temp 55-110°F |
| `button.eight_sleep_left_stop_alarm` | button | Clear active alarm |
| `button.eight_sleep_left_trigger_alarm` | button | Fire alarm instantly |
| `text.eight_sleep_left_alarm_schedule` | text | JSON alarm schedule (all days) |
| *(existing sensors)* | sensor | current_temp, target_temp, seconds_remaining |
| *(existing binary sensors)* | binary_sensor | is_on, is_alarm_vibrating |

### Eight Sleep – Right

| Entity ID | Type | Description |
|-----------|------|-------------|
| `switch.eight_sleep_right_power` | switch | Turn side on/off |
| `number.eight_sleep_right_temperature` | number | Target temp 55-110°F |
| `button.eight_sleep_right_stop_alarm` | button | Clear active alarm |
| `button.eight_sleep_right_trigger_alarm` | button | Fire alarm instantly |
| `text.eight_sleep_right_alarm_schedule` | text | JSON alarm schedule (all days) |
| *(existing sensors)* | sensor | current_temp, target_temp, seconds_remaining |
| *(existing binary sensors)* | binary_sensor | is_on, is_alarm_vibrating |

### Eight Sleep – Hub

| Entity ID | Type | Description |
|-----------|------|-------------|
| `button.eight_sleep_prime_pod` | button | Start priming process |
| `switch.eight_sleep_sync_mode` | switch | Sync temp/power to both sides |
| `switch.eight_sleep_instant_alarm_sync` | switch | Trigger alarm on both sides |
| `number.eight_sleep_instant_alarm_intensity` | number | Vibration strength 1-100 |
| `select.eight_sleep_instant_alarm_pattern` | select | "rise" or "double" |
| `number.eight_sleep_instant_alarm_duration` | number | Duration 0-180 seconds |
| *(existing binary sensors)* | binary_sensor | is_priming, water_level |

---

## Sync Mode Behavior

### `switch.eight_sleep_sync_mode` (default: OFF)

When **ON**, the following actions apply to BOTH sides:
- Setting temperature (number entity)
- Turning power on/off (switch entity)
- Stopping alarm (button entity)

### `switch.eight_sleep_instant_alarm_sync` (default: OFF)

When **ON**:
- Pressing either trigger_alarm button fires alarm on BOTH sides

---

## Instant Alarm Behavior

When `button.eight_sleep_left_trigger_alarm` or `button.eight_sleep_right_trigger_alarm` is pressed:

1. Read current values from:
   - `number.eight_sleep_instant_alarm_intensity`
   - `select.eight_sleep_instant_alarm_pattern`
   - `number.eight_sleep_instant_alarm_duration`

2. POST to `/api/alarm`:
   ```json
   {
     "side": "left",
     "vibrationIntensity": <intensity>,
     "vibrationPattern": "<pattern>",
     "duration": <duration>
   }
   ```

3. If `switch.eight_sleep_instant_alarm_sync` is ON:
   - Also POST with `"side": "right"`

---

## Alarm Schedule Text Entity

### Format

JSON string containing alarm settings for all 7 days:

```json
{
  "monday": {
    "time": "07:00",
    "enabled": true,
    "alarmTemperature": 85,
    "vibrationIntensity": 80,
    "vibrationPattern": "rise",
    "duration": 60
  },
  "tuesday": { ... },
  "wednesday": { ... },
  "thursday": { ... },
  "friday": { ... },
  "saturday": { ... },
  "sunday": { ... }
}
```

### Behavior

- **Read**: GET `/api/schedules` → extract alarm data for side
- **Write**: User pastes JSON → POST `/api/schedules` with updated alarm data

### Field Constraints

| Field | Type | Range |
|-------|------|-------|
| time | string | "HH:mm" format |
| enabled | boolean | true/false |
| alarmTemperature | integer | 55-110 |
| vibrationIntensity | integer | 1-100 |
| vibrationPattern | string | "rise" or "double" |
| duration | integer | 0-180 |

---

## API Endpoints Used

| Feature | Method | Endpoint | Payload |
|---------|--------|----------|---------|
| Set temperature | POST | `/api/deviceStatus` | `{"left": {"targetTemperatureF": 85}}` |
| Turn on | POST | `/api/deviceStatus` | `{"left": {"isOn": true, "secondsRemaining": 43200}}` |
| Turn off | POST | `/api/deviceStatus` | `{"left": {"isOn": false}}` |
| Stop alarm | POST | `/api/deviceStatus` | `{"left": {"isAlarmVibrating": false}}` |
| Start priming | POST | `/api/deviceStatus` | `{"isPriming": true}` |
| Trigger alarm | POST | `/api/alarm` | `{"side": "left", "vibrationIntensity": 80, ...}` |
| Get schedules | GET | `/api/schedules` | - |
| Update schedules | POST | `/api/schedules` | `{"left": {"monday": {"alarm": {...}}}}` |

---

## Default Values

| Setting | Default |
|---------|---------|
| Sync Mode | OFF |
| Instant Alarm Sync | OFF |
| Instant Alarm Intensity | 80 |
| Instant Alarm Pattern | "rise" |
| Instant Alarm Duration | 60 |
| Power On Duration | 43200 (12 hours) |

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `localEight/device.py` | Add POST methods for all API calls |
| `switch.py` | Create - power switches, sync toggles |
| `number.py` | Create - temperature, alarm intensity/duration |
| `button.py` | Create - stop alarm, trigger alarm, prime pod |
| `select.py` | Create - alarm pattern selection |
| `text.py` | Create - alarm schedule JSON |
| `__init__.py` | Add new platforms |
| `const.py` | Add new constants |

---

## Implementation Priority

1. **Phase 1**: API client methods (device.py)
2. **Phase 2**: switch.py (power on/off, sync modes)
3. **Phase 3**: number.py (temperature, alarm settings)
4. **Phase 4**: button.py (stop/trigger alarm, prime)
5. **Phase 5**: select.py (alarm pattern)
6. **Phase 6**: text.py (alarm schedule)
