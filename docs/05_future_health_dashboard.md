# 05 - Future: Health Dashboard

**Status**: Pending (implement after core features from 04_feature_requirements.md)

---

## Overview

Health metrics feature to expose biometric data from the Eight Sleep pod.

**Note from README**: "Exposing health metrics – Waiting for upstream go ahead"

---

## Available API Endpoints

### GET `/api/metrics/vitals`

Query params: `side`, `startTime`, `endTime`

Returns heart rate, HRV, breathing rate records over time.

### GET `/api/metrics/vitals/summary`

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

### GET `/api/metrics/sleep`

Query params: `side`, `startTime`, `endTime`

Returns sleep interval records (entered_bed_at, left_bed_at, times_exited_bed, etc.)

---

## Potential Entities

| Entity | Type | Description |
|--------|------|-------------|
| `sensor.eight_sleep_left_avg_heart_rate` | sensor | Average heart rate (bpm) |
| `sensor.eight_sleep_left_min_heart_rate` | sensor | Min heart rate (bpm) |
| `sensor.eight_sleep_left_max_heart_rate` | sensor | Max heart rate (bpm) |
| `sensor.eight_sleep_left_avg_hrv` | sensor | Average HRV (ms) |
| `sensor.eight_sleep_left_breathing_rate` | sensor | Breathing rate (breaths/min) |
| `sensor.eight_sleep_left_sleep_duration` | sensor | Last sleep duration |
| `sensor.eight_sleep_left_times_exited_bed` | sensor | Times left bed |

Same for right side.

---

## Implementation Notes

- Requires biometrics to be enabled on pod: `sh /home/dac/free-sleep/scripts/enable_biometrics.sh`
- Data stored in SQLite on pod: `/persistent/free-sleep-data/free-sleep.db`
- Heart rate validated, HRV & breathing rate may be inaccurate (per README)
- Consider polling interval - vitals update every 60 seconds

---

## Next Steps

1. Confirm upstream approval for health metrics
2. Design time range selection (last night, last 7 days, etc.)
3. Implement sensors with appropriate polling
