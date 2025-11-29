# 07 - Local Development & Testing

Guide for running the free-sleep server locally without hardware for testing the Home Assistant integration.

---

## Project Locations (Windows)

```
C:\Users\Felix\PycharmProjects\freesleep_combo\
├── free-sleep/           # Node.js server (runs on pod, or locally for dev)
└── eight-sleep-local/    # Home Assistant custom integration
```

---

## Free-Sleep Server Local Dev Mode

### What is remoteDevMode?

When `ENV=local`, the server runs in `remoteDevMode`:
- Skips Franken/device connection (no hardware needed)
- Uses local data folder instead of pod paths
- API routes are accessible for testing

### Setup Steps

1. **Update `.env.local`** in `free-sleep/server/`:

```env
ENV="local"
DATA_FOLDER="./free-sleep-data/"
DATABASE_URL="file:./free-sleep-data/free-sleep.db"
```

2. **Install dependencies:**
```bash
cd free-sleep/server
npm install
```

3. **Generate Prisma client:**
```bash
npm run generate:local
```

4. **Run the server:**
```bash
npm run dev:local
```

Server runs at `http://localhost:3000`

---

## API Endpoints Available in Dev Mode

| Endpoint | Method | Works in Dev? | Notes |
|----------|--------|---------------|-------|
| `/api/deviceStatus` | GET | ❌ | Needs device |
| `/api/deviceStatus` | POST | ❌ | Needs device |
| `/api/presence` | GET | ✅ | Returns default/stored values |
| `/api/services` | GET/POST | ✅ | Works (lowdb storage) |
| `/api/schedules` | GET/POST | ✅ | Works (lowdb storage) |
| `/api/settings` | GET/POST | ✅ | Works (lowdb storage) |
| `/api/metrics/vitals` | GET | ✅ | Needs data in SQLite |
| `/api/metrics/sleep` | GET | ✅ | Needs data in SQLite |

---

## Testing the HA Integration

### Option 1: Mock deviceStatus endpoint

Create a simple mock that returns fake device data. Add to `free-sleep/server/src/routes/deviceStatus/deviceStatus.ts`:

```typescript
// Add mock data for dev mode
import config from '../../config.js';

router.get('/deviceStatus', async (req: Request, res: Response) => {
  if (config.remoteDevMode) {
    // Return mock data in dev mode
    res.json({
      left: {
        currentTemperatureF: 75,
        targetTemperatureF: 80,
        secondsRemaining: 3600,
        isAlarmVibrating: false,
        isOn: true,
      },
      right: {
        currentTemperatureF: 72,
        targetTemperatureF: 78,
        secondsRemaining: 3600,
        isAlarmVibrating: false,
        isOn: true,
      },
      waterLevel: "true",
      isPriming: false,
      sensorLabel: "mock-device",
    });
    return;
  }
  // ... existing code
});
```

### Option 2: Test individual endpoints

Use curl or Postman to test specific endpoints:

```bash
# Test presence endpoint
curl http://localhost:3000/api/presence

# Test services endpoint
curl http://localhost:3000/api/services

# Test schedules endpoint
curl http://localhost:3000/api/schedules
```

---

## WSL Setup (Linux Environment)

If running in WSL:

1. **Clone/access the project:**
```bash
cd /mnt/c/Users/Felix/PycharmProjects/freesleep_combo/free-sleep/server
```

2. **Install Node.js (via volta or nvm):**
```bash
# Using volta (recommended - matches project)
curl https://get.volta.sh | bash
volta install node@24

# Or using nvm
nvm install 24
nvm use 24
```

3. **Update `.env.local` for WSL paths:**
```env
ENV="local"
DATA_FOLDER="./free-sleep-data/"
DATABASE_URL="file:./free-sleep-data/free-sleep.db"
```

4. **Run setup:**
```bash
npm install
npm run generate:local
npm run dev:local
```

5. **Access from Windows:**
- Server available at `http://localhost:3000` (WSL2 forwards ports automatically)

---

## Seeding Test Data

To test health metrics, you need data in SQLite. Create a seed script or manually insert:

```sql
-- Insert test vitals
INSERT INTO vitals (side, timestamp, heart_rate, hrv, breathing_rate)
VALUES
  ('left', strftime('%s', 'now') - 3600, 62, 45, 14),
  ('left', strftime('%s', 'now') - 3000, 60, 48, 13),
  ('right', strftime('%s', 'now') - 3600, 58, 52, 15);

-- Insert test sleep record
INSERT INTO sleep_records (side, entered_bed_at, left_bed_at, sleep_period_seconds, times_exited_bed, present_intervals, not_present_intervals)
VALUES
  ('left', strftime('%s', 'now') - 28800, strftime('%s', 'now'), 28800, 1, '[]', '[]');
```

---

## Files Modified for Dev Mode

| File | Change |
|------|--------|
| `server/src/config.ts` | Detects `ENV=local` → `remoteDevMode=true` |
| `server/src/server.ts` | Skips Franken init when `remoteDevMode` |
| `server/.env.local` | Local environment variables |

---

## Limitations in Dev Mode

1. **No device control** - POST to deviceStatus won't actually change anything
2. **No real presence detection** - Biometrics stream doesn't run
3. **No real vitals** - Need to seed database with test data
4. **Schedules won't execute** - Jobs that control device are skipped
