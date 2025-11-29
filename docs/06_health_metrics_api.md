# 06 - Health Metrics API Analysis

Analysis of the free-sleep health metrics API for future implementation.

---

## API Endpoints Overview

### 1. GET `/api/metrics/vitals`

**Purpose**: Get raw vitals data (heart rate, HRV, breathing rate) over time.

**Query Parameters**:
| Param | Type | Description |
|-------|------|-------------|
| `side` | string | "left" or "right" |
| `startTime` | string | ISO datetime or parseable date |
| `endTime` | string | ISO datetime or parseable date |

**Response**: Array of vital records
```json
[
  {
    "id": 1,
    "side": "left",
    "timestamp": "2025-01-10T23:30:00-05:00",
    "heart_rate": 62,
    "hrv": 45,
    "breathing_rate": 14
  },
  ...
]
```

**Notes**:
- Records are inserted every 60 seconds when presence is detected
- Timestamps are converted to user's timezone

---

### 2. GET `/api/metrics/vitals/summary`

**Purpose**: Get aggregated vitals summary for a time period.

**Query Parameters**: Same as `/vitals`

**Response**:
```json
{
  "avgHeartRate": 62,
  "minHeartRate": 55,
  "maxHeartRate": 85,
  "avgHRV": 45,
  "avgBreathingRate": 14
}
```

**Notes**:
- Breathing rate excludes values outside 5-20 range
- HRV excludes values outside 30-120 range
- All values rounded to integers

---

### 3. GET `/api/metrics/sleep`

**Purpose**: Get sleep session records.

**Query Parameters**:
| Param | Type | Description |
|-------|------|-------------|
| `side` | string | "left" or "right" |
| `startTime` | string | Filter by `left_bed_at >= startTime` |
| `endTime` | string | Filter by `entered_bed_at <= endTime` |

**Response**: Array of sleep records
```json
[
  {
    "id": 1,
    "side": "left",
    "entered_bed_at": "2025-01-10T22:30:00-05:00",
    "left_bed_at": "2025-01-11T06:45:00-05:00",
    "sleep_period_seconds": 29700,
    "times_exited_bed": 2,
    "present_intervals": [
      ["2025-01-10T22:30:00-05:00", "2025-01-11T02:15:00-05:00"],
      ["2025-01-11T02:20:00-05:00", "2025-01-11T06:45:00-05:00"]
    ],
    "not_present_intervals": [
      ["2025-01-11T02:15:00-05:00", "2025-01-11T02:20:00-05:00"]
    ]
  }
]
```

**Calculated Fields**:
- `sleep_period_seconds`: Total time from entered to left bed
- `times_exited_bed`: Count of not_present_intervals
- `present_intervals`: Time ranges when in bed
- `not_present_intervals`: Time ranges when out of bed

---

### 4. GET `/api/metrics/movement`

**Purpose**: Get movement data over time.

**Query Parameters**: Same as `/vitals`

**Response**: Array of movement records
```json
[
  {
    "id": 1,
    "side": "left",
    "timestamp": "2025-01-10T23:30:00-05:00",
    "total_movement": 150
  },
  ...
]
```

---

## Data Collection Requirements

**Important**: Biometrics require:
1. Biometrics enabled on pod: `sh /home/dac/free-sleep/scripts/enable_biometrics.sh`
2. Pod internet blocked (data only available when pod can't reach cloud)
3. Data stored in SQLite: `/persistent/free-sleep-data/free-sleep.db`

---

## Data Accuracy (from README)

| Metric | Accuracy | Notes |
|--------|----------|-------|
| Heart Rate | **Validated** | RMSE 2.88 avg, 80.8% correlation vs Apple Watch |
| HRV | Not validated | May be inaccurate |
| Breathing Rate | Not validated | May be inaccurate |

Heart rate slightly less accurate for females.

---

## Sensor Data Sources

### Capacitance Sensors
- Measures pressure every 1 second
- 3 sensors per side (out, cen, in)
- Used for presence detection

### Piezo Sensors
- Measures pressure 500x per second
- Pod 3: 2 sensors, Pod 4: 1 sensor
- Used for heart rate, HRV, breathing calculations

---

## Proposed Home Assistant Entities

### Per Side (Left/Right)

| Entity | Type | Unit | Description |
|--------|------|------|-------------|
| `sensor.eight_sleep_{side}_heart_rate` | sensor | bpm | Current/last heart rate |
| `sensor.eight_sleep_{side}_heart_rate_avg` | sensor | bpm | Average (last night) |
| `sensor.eight_sleep_{side}_heart_rate_min` | sensor | bpm | Min (last night) |
| `sensor.eight_sleep_{side}_heart_rate_max` | sensor | bpm | Max (last night) |
| `sensor.eight_sleep_{side}_hrv` | sensor | ms | Average HRV (last night) |
| `sensor.eight_sleep_{side}_breathing_rate` | sensor | /min | Average breathing rate |
| `sensor.eight_sleep_{side}_sleep_duration` | sensor | hours | Last sleep duration |
| `sensor.eight_sleep_{side}_times_out_of_bed` | sensor | count | Times left bed |
| `sensor.eight_sleep_{side}_bed_presence` | binary_sensor | - | Currently in bed |

---

## Implementation Considerations

### Time Range Options

For summary sensors, need to decide time range strategy:

**Option A**: Fixed "last night" (e.g., 8pm yesterday to 10am today)
- Simple but may miss late sleepers

**Option B**: Use last sleep record's time range
- More accurate but requires fetching sleep records first

**Option C**: Rolling 24 hours
- Simple but includes daytime data

**Option D**: User-configurable
- Most flexible but complex

### Polling Frequency

- Vitals update every 60 seconds on pod
- Summary data doesn't change during day
- Suggestion: Poll vitals every 5 min, summary once per hour or on-demand

### Presence Detection

- Can be derived from recent vitals records (if records exist, person is present)
- Or create separate presence detection logic

---

## API Client Methods to Add

```python
async def get_vitals(
    self,
    side: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None
) -> list[dict]:
    """Get raw vitals records."""
    params = {}
    if side: params["side"] = side
    if start_time: params["startTime"] = start_time
    if end_time: params["endTime"] = end_time
    return await self.api_request("GET", f"/api/metrics/vitals?{urlencode(params)}", None)

async def get_vitals_summary(
    self,
    side: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None
) -> dict:
    """Get vitals summary (avg/min/max)."""
    params = {}
    if side: params["side"] = side
    if start_time: params["startTime"] = start_time
    if end_time: params["endTime"] = end_time
    return await self.api_request("GET", f"/api/metrics/vitals/summary?{urlencode(params)}", None)

async def get_sleep_records(
    self,
    side: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None
) -> list[dict]:
    """Get sleep session records."""
    params = {}
    if side: params["side"] = side
    if start_time: params["startTime"] = start_time
    if end_time: params["endTime"] = end_time
    return await self.api_request("GET", f"/api/metrics/sleep?{urlencode(params)}", None)

async def get_movement(
    self,
    side: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None
) -> list[dict]:
    """Get movement records."""
    params = {}
    if side: params["side"] = side
    if start_time: params["startTime"] = start_time
    if end_time: params["endTime"] = end_time
    return await self.api_request("GET", f"/api/metrics/movement?{urlencode(params)}", None)
```

---

## Implementation Decisions

### Polling Frequency

| Data Type | Poll Interval | Rationale |
|-----------|---------------|-----------|
| Device status (temp, power) | 5s (configurable) | Real-time control |
| Vitals/health metrics | 60s minimum | Data only updates every 60s on pod |

### Time Range for Summary Stats

**Decision**: Use last sleep record's `entered_bed_at` → `left_bed_at`

```
TODO: Handle multiple intervals
- What if user gets up at night? Could create gaps in data
- Sleep record has `present_intervals` array - may need to query
  vitals for each interval separately and aggregate
- Or just use full sleep period and accept gaps in data
```

### Presence Detection

**Status**: ✅ IMPLEMENTED

**Endpoint**: `GET /api/presence`

**Response**:
```json
{
  "left": { "present": true, "lastUpdated": "2025-01-15T08:30:00Z" },
  "right": { "present": false, "lastUpdated": "2025-01-15T07:45:00Z" }
}
```

**Per-side endpoint**: `GET /api/presence/{side}` (where side is "left" or "right")

**Response**:
```json
{ "present": true, "lastUpdated": "2025-01-15T08:30:00Z" }
```

**Implementation Details (free-sleep)**:
- Presence is detected via piezo sensor signal range (threshold: >200,000)
- The biometrics stream processor (`stream_processor.py`) posts presence updates to `/api/services` when presence changes
- The `/api/presence` endpoint reads from the services data store
- Updates are real-time (posted on each state change, not polled)

**Requirements**:
- Biometrics must be enabled for presence detection to work
- Presence data is only updated while the biometrics stream service is running

---

## API Client Methods to Add

```python
async def get_presence(self) -> dict:
    """Get presence status for both sides."""
    return await self.api_request("GET", "/api/presence", None)

async def get_presence_side(self, side: str) -> dict:
    """Get presence status for a specific side (left or right)."""
    return await self.api_request("GET", f"/api/presence/{side}", None)
```

---

## Next Steps

1. ~~**free-sleep**: Implement presence endpoint~~ ✅ DONE
2. ~~**eight-sleep-local**: Add API client methods for health metrics and presence~~ ✅ DONE
3. ~~**eight-sleep-local**: Create health sensor entities with 60s poll minimum~~ ✅ DONE
4. ~~**eight-sleep-local**: Create presence binary_sensor~~ ✅ DONE
5. Use sleep records for time range, handle intervals (implemented - uses last sleep record)

## Implemented Health Sensors

Per side (left/right):
- `sensor.eight_sleep_{side}_heart_rate` - Average heart rate (last night)
- `sensor.eight_sleep_{side}_heart_rate_min` - Minimum heart rate (last night)
- `sensor.eight_sleep_{side}_heart_rate_max` - Maximum heart rate (last night)
- `sensor.eight_sleep_{side}_hrv` - Average HRV (last night)
- `sensor.eight_sleep_{side}_breathing_rate` - Average breathing rate (last night)
- `sensor.eight_sleep_{side}_sleep_duration` - Sleep duration in hours (last night)
- `sensor.eight_sleep_{side}_times_out_of_bed` - Times left bed (last night)
- `binary_sensor.eight_sleep_{side}_bed_presence` - Currently in bed
