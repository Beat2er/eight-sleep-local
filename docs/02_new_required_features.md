# 02 - New Required Features

Based on the README "In Progress / Help Wanted" section and the `translations/en.json` service definitions, this document defines the features to implement.

---

## Feature 1: Temperature Control

### 1.1 Set Temperature (heat_set)

**User Story**: As a Home Assistant user, I want to set the target temperature for my bed side so I can control the bed temperature from automations.

**API Call**:
```http
POST /api/deviceStatus
Content-Type: application/json

{
  "left": {                        // or "right"
    "targetTemperatureF": 85,      // 55-110
    "secondsRemaining": 3600       // optional: duration in seconds
  }
}
```

**Home Assistant Service**:
```yaml
service: eight_sleep_local.heat_set
target:
  entity_id: sensor.eight_sleep_left_current_temperature
data:
  target: 85                       # Temperature in Fahrenheit
  duration: 3600                   # Optional: seconds
```

**Implementation Requirements**:
- Add `set_temperature(side, temperature_f, duration=None)` method to `LocalEightSleep`
- Create service `heat_set` in Home Assistant
- Validate temperature range (55-110°F)
- Duration default: 12 hours (43200 seconds) when turning on

### 1.2 Turn Side On/Off (side_on, side_off)

**User Story**: As a Home Assistant user, I want to turn my bed side on or off.

**API Call - Turn On**:
```http
POST /api/deviceStatus
Content-Type: application/json

{
  "left": {
    "isOn": true,
    "secondsRemaining": 43200      // 12 hours default
  }
}
```

**API Call - Turn Off**:
```http
POST /api/deviceStatus
Content-Type: application/json

{
  "left": {
    "isOn": false
  }
}
```

**Home Assistant Services**:
```yaml
service: eight_sleep_local.side_on
target:
  entity_id: binary_sensor.eight_sleep_left_side_on

service: eight_sleep_local.side_off
target:
  entity_id: binary_sensor.eight_sleep_left_side_on
```

**Implementation Requirements**:
- Add `turn_on(side, duration=43200)` method to `LocalEightSleep`
- Add `turn_off(side)` method to `LocalEightSleep`
- Create services `side_on` and `side_off`

### 1.3 Climate Entity (Alternative/Enhancement)

**Consideration**: Instead of just services, expose each side as a `climate` entity for native thermostat-like control in Home Assistant.

**Benefits**:
- Native temperature slider in HA UI
- Works with generic thermostat cards
- HVAC modes: off, heat, cool (or just "heat" for simplicity)

---

## Feature 2: Alarm Control

### 2.1 Stop/Clear Alarm (alarm_stop)

**User Story**: As a Home Assistant user, I want to stop an active alarm vibration.

**API Call**:
```http
POST /api/deviceStatus
Content-Type: application/json

{
  "left": {
    "isAlarmVibrating": false
  }
}
```

**Home Assistant Service**:
```yaml
service: eight_sleep_local.alarm_stop
target:
  entity_id: binary_sensor.eight_sleep_left_alarm_active
```

**Implementation Requirements**:
- Add `stop_alarm(side)` method to `LocalEightSleep`
- Create service `alarm_stop`

### 2.2 Snooze Alarm (alarm_snooze)

**User Story**: As a Home Assistant user, I want to snooze an alarm for a specified duration.

**Note**: The free-sleep API doesn't have a direct "snooze" endpoint. Snooze can be implemented by:
1. Stopping the current alarm
2. Scheduling a new alarm after the snooze duration

**API Calls**:
```http
# 1. Clear current alarm
POST /api/deviceStatus
{
  "left": { "isAlarmVibrating": false }
}

# 2. Execute new alarm after delay (handled client-side or via HA automation)
POST /api/alarm
{
  "side": "left",
  "vibrationIntensity": 100,
  "vibrationPattern": "rise",
  "duration": 60,
  "force": true
}
```

**Home Assistant Service**:
```yaml
service: eight_sleep_local.alarm_snooze
target:
  entity_id: binary_sensor.eight_sleep_left_alarm_active
data:
  duration: 9                      # Minutes to snooze
```

**Implementation Options**:
1. **Simple**: Just stop the alarm, let user create HA automation for re-trigger
2. **Advanced**: Use HA's `async_call_later` to schedule re-execution

### 2.3 Execute Alarm (alarm_trigger - new)

**User Story**: As a Home Assistant user, I want to manually trigger an alarm vibration (e.g., for testing or custom wake scenarios).

**API Call**:
```http
POST /api/alarm
Content-Type: application/json

{
  "side": "left",
  "vibrationIntensity": 80,        // 1-100
  "vibrationPattern": "rise",      // "rise" or "double"
  "duration": 60                   // seconds, max 180
}
```

**Home Assistant Service**:
```yaml
service: eight_sleep_local.alarm_trigger
target:
  entity_id: binary_sensor.eight_sleep_left_alarm_active
data:
  intensity: 80
  pattern: rise
  duration: 60
```

---

## Feature 3: Device Control

### 3.1 Prime Pod (prime_pod)

**User Story**: As a Home Assistant user, I want to start the priming process.

**API Call**:
```http
POST /api/deviceStatus
Content-Type: application/json

{
  "isPriming": true
}
```

**Home Assistant Service**:
```yaml
service: eight_sleep_local.prime_pod
# No target needed - applies to hub
```

**Implementation Requirements**:
- Add `start_priming()` method to `LocalEightSleep`
- Create service `prime_pod`

---

## Feature 4: Health Metrics (Future - Waiting for Upstream)

### 4.1 Vitals Sensors

**Sensors to expose**:
| Sensor | API Source | Unit |
|--------|------------|------|
| Heart Rate (avg) | /api/metrics/vitals/summary | bpm |
| Heart Rate (min) | /api/metrics/vitals/summary | bpm |
| Heart Rate (max) | /api/metrics/vitals/summary | bpm |
| HRV (avg) | /api/metrics/vitals/summary | ms |
| Breathing Rate | /api/metrics/vitals/summary | breaths/min |

**API Call**:
```http
GET /api/metrics/vitals/summary?side=left&startTime=2024-01-01&endTime=2024-01-02
```

**Note**: This feature is marked as "Waiting for upstream go ahead" in the README. Implementation should be deferred until confirmed.

---

## Feature Priority

| Priority | Feature | Complexity | README Listed |
|----------|---------|------------|---------------|
| 1 | Set Temperature | Medium | Yes |
| 2 | Turn On/Off | Low | Implied |
| 3 | Stop Alarm | Low | Yes |
| 4 | Prime Pod | Low | No (but useful) |
| 5 | Snooze Alarm | Medium | Yes |
| 6 | Trigger Alarm | Medium | No (but useful) |
| 7 | Climate Entity | High | No (enhancement) |
| 8 | Health Metrics | High | Yes (deferred) |

---

## Entity Types Summary

### Current (sensor.py)
- `sensor` platform: Temperature values
- `binary_sensor`: isOn, isAlarmVibrating, isPriming, waterLevel

### Proposed Additions
- `switch` platform: For on/off control per side
- `number` platform: For temperature setting per side
- OR `climate` platform: Combined thermostat-like control
- `button` platform: For prime_pod, alarm_stop actions

---

## Services Definition (services.yaml)

A `services.yaml` file needs to be created to properly register services:

```yaml
heat_set:
  name: Set Temperature
  description: Set the target temperature for a bed side
  target:
    entity:
      integration: eight_sleep_local
  fields:
    target:
      name: Target Temperature
      description: Target temperature in Fahrenheit (55-110)
      required: true
      selector:
        number:
          min: 55
          max: 110
          unit_of_measurement: "°F"
    duration:
      name: Duration
      description: Duration in seconds (optional)
      required: false
      selector:
        number:
          min: 0
          max: 86400
          unit_of_measurement: "s"

side_on:
  name: Turn Side On
  description: Turn on a bed side
  target:
    entity:
      integration: eight_sleep_local

side_off:
  name: Turn Side Off
  description: Turn off a bed side
  target:
    entity:
      integration: eight_sleep_local

alarm_stop:
  name: Stop Alarm
  description: Stop an active alarm
  target:
    entity:
      integration: eight_sleep_local

alarm_snooze:
  name: Snooze Alarm
  description: Snooze alarm for specified minutes
  target:
    entity:
      integration: eight_sleep_local
  fields:
    duration:
      name: Duration
      description: Snooze duration in minutes
      required: true
      selector:
        number:
          min: 1
          max: 60
          unit_of_measurement: "min"

prime_pod:
  name: Prime Pod
  description: Start the pod priming process
```
