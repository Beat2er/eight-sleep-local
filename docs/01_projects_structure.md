# 01 - Projects Structure

## eight-sleep-local (Target Project)

### Directory Structure

```
eight-sleep-local/
├── .devcontainer/
│   └── devcontainer.json
├── custom_components/
│   └── eight_sleep_local/
│       ├── localEight/
│       │   └── device.py          # API client for free-sleep server
│       ├── translations/
│       │   └── en.json            # Service definitions (some not implemented)
│       ├── __init__.py            # Integration setup, platforms: ["sensor"]
│       ├── config_flow.py         # Configuration UI (host, port)
│       ├── const.py               # Constants (DOMAIN, CONF_HOST, CONF_PORT)
│       ├── manifest.json          # Integration manifest
│       └── sensor.py              # Sensor entities (temperature, alarm, etc.)
├── hacs.json
└── README.md
```

### Key Files Analysis

#### `__init__.py`
- Sets up integration via config flow
- Only loads `sensor` platform currently
- Stores config in `hass.data[DOMAIN][entry.entry_id]`

#### `sensor.py`
- **Coordinator**: `EightSleepDataUpdateCoordinator` - polls every 5 seconds
- **Entities**:
  - `EightSleepSensor` - for numeric values (temperatures, seconds)
  - `EightSleepBinarySensor` - for boolean values (isOn, isAlarmVibrating, isPriming)
- **Sensor Types**:
  | Key | Name | Type | JSON Key |
  |-----|------|------|----------|
  | current_temp_f | Current Temperature | sensor | currentTemperatureF |
  | target_temp_f | Target Temperature | sensor | targetTemperatureF |
  | seconds_remaining | Seconds Remaining | sensor | secondsRemaining |
  | is_alarm_vibrating | Alarm Active | binary | isAlarmVibrating |
  | is_on | Side On | binary | isOn |
  | is_priming | Is Priming | binary | isPriming |
  | water_level | Water Level | binary | waterLevel |

#### `localEight/device.py`
- `LocalEightSleep` class - aiohttp-based API client
- **Current capabilities**:
  - `start()` / `stop()` - session management
  - `update_device_data()` - GET `/api/deviceStatus`
  - `api_request(method, api_slug, data)` - generic request method
- **Missing capabilities**:
  - No POST methods for temperature control
  - No alarm control methods
  - No metrics endpoints

#### `translations/en.json`
Contains service definitions that are **NOT YET IMPLEMENTED**:
- `heat_set` - Set heating/cooling level
- `heat_increment` - Offset current level
- `side_off` / `side_on` - Turn side off/on
- `alarm_snooze` / `alarm_stop` / `alarm_dismiss` - Alarm controls
- `away_mode_start` / `away_mode_stop` - Away mode
- `prime_pod` - Start priming

---

## free-sleep (Reference Project)

### Directory Structure

```
free-sleep/
├── app/                           # React frontend (not relevant)
├── biometrics/                    # Python scripts for vitals
├── docs/                          # Screenshots
├── scripts/                       # Shell scripts
├── server/                        # Express.js backend (OUR REFERENCE)
│   ├── src/
│   │   ├── 8sleep/               # Device communication
│   │   │   ├── deviceApi.ts      # Command definitions & execution
│   │   │   ├── frankenServer.ts  # Unix socket communication
│   │   │   └── loadDeviceStatus.ts
│   │   ├── db/                   # Database schemas
│   │   │   ├── schedulesSchema.ts # Alarm/schedule types
│   │   │   └── settingsSchema.ts
│   │   ├── jobs/                 # Scheduled tasks
│   │   │   └── alarmScheduler.ts # Alarm execution logic
│   │   └── routes/               # API endpoints
│   │       ├── alarm/alarm.ts
│   │       ├── deviceStatus/
│   │       │   ├── deviceStatus.ts
│   │       │   ├── deviceStatusSchema.ts
│   │       │   └── updateDeviceStatus.ts
│   │       ├── execute/execute.ts
│   │       └── metrics/
│   │           ├── vitals.ts
│   │           └── sleep.ts
│   └── package.json
└── README.md
```

### API Endpoints Detail

#### GET `/api/deviceStatus`
Returns current device state:
```typescript
{
  left: {
    currentTemperatureLevel: number,
    currentTemperatureF: number,
    targetTemperatureF: number,      // 55-110
    secondsRemaining: number,
    isOn: boolean,
    isAlarmVibrating: boolean,
    taps?: { doubleTap, tripleTap, quadTap }
  },
  right: { /* same as left */ },
  waterLevel: string,
  isPriming: boolean,
  settings: {
    v: number,
    gainLeft: number,
    gainRight: number,
    ledBrightness: number
  },
  coverVersion: string,
  hubVersion: string,
  freeSleep: { version, branch },
  wifiStrength: number
}
```

#### POST `/api/deviceStatus`
Update device state. Partial updates supported.

**Temperature Control**:
```json
{
  "left": {
    "targetTemperatureF": 85,
    "isOn": true,
    "secondsRemaining": 3600
  }
}
```

**Clear Alarm**:
```json
{
  "left": {
    "isAlarmVibrating": false
  }
}
```

**Start Priming**:
```json
{
  "isPriming": true
}
```

#### POST `/api/alarm`
Execute alarm vibration:
```typescript
{
  side: "left" | "right",
  vibrationIntensity: number,  // 1-100
  vibrationPattern: "double" | "rise",
  duration: number,            // seconds, 0-180
  force?: boolean              // override away mode/off state
}
```

#### POST `/api/execute`
Raw command execution:
```typescript
{
  command: string,  // e.g., "ALARM_CLEAR", "PRIME"
  arg?: string
}
```

Available commands (from `deviceApi.ts`):
| Command | Code | Purpose |
|---------|------|---------|
| HELLO | 0 | Ping |
| SET_TEMP | 1 | Set temperature |
| SET_ALARM | 2 | Configure alarm |
| ALARM_LEFT | 5 | Trigger left alarm |
| ALARM_RIGHT | 6 | Trigger right alarm |
| SET_SETTINGS | 8 | Update settings |
| LEFT_TEMP_DURATION | 9 | Left side duration |
| RIGHT_TEMP_DURATION | 10 | Right side duration |
| TEMP_LEVEL_LEFT | 11 | Left temperature level |
| TEMP_LEVEL_RIGHT | 12 | Right temperature level |
| PRIME | 13 | Start priming |
| DEVICE_STATUS | 14 | Get status |
| ALARM_CLEAR | 16 | Clear alarm |

#### GET `/api/metrics/vitals`
Query params: `side`, `startTime`, `endTime`
Returns heart rate, HRV, breathing rate records.

#### GET `/api/metrics/vitals/summary`
Query params: `side`, `startTime`, `endTime`
Returns:
```json
{
  "avgHeartRate": 62,
  "minHeartRate": 55,
  "maxHeartRate": 85,
  "avgHRV": 45,
  "avgBreathingRate": 14
}
```

#### GET `/api/metrics/sleep`
Query params: `side`, `startTime`, `endTime`
Returns sleep interval records.

---

## Temperature Conversion Formula

From `updateDeviceStatus.ts`:
```typescript
const calculateLevelFromF = (temperatureF: number) => {
  const level = (temperatureF - 82.5) / 27.5 * 100;
  return Math.round(level).toString();
};
```

- Temperature range: 55°F to 110°F
- Level range: -100 to +100
- 82.5°F = level 0 (neutral)

---

## Current Implementation Gap Summary

| Feature | free-sleep API | eight-sleep-local |
|---------|---------------|-------------------|
| Read device status | GET /api/deviceStatus | Implemented |
| Set temperature | POST /api/deviceStatus | **NOT IMPLEMENTED** |
| Turn on/off | POST /api/deviceStatus | **NOT IMPLEMENTED** |
| Clear alarm | POST /api/deviceStatus | **NOT IMPLEMENTED** |
| Start priming | POST /api/deviceStatus | **NOT IMPLEMENTED** |
| Execute alarm | POST /api/alarm | **NOT IMPLEMENTED** |
| Health metrics | GET /api/metrics/* | **NOT IMPLEMENTED** |
