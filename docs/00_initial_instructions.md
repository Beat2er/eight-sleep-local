# 00 - Initial Instructions

## Project Overview

This documentation tracks the implementation of new features for the **eight-sleep-local** Home Assistant integration. The goal is to implement the "In Progress / Help Wanted" features listed in the README while using **free-sleep** as a reference for API endpoints.

## Constraints

1. **DO NOT modify free-sleep** - It serves only as a reference for API endpoints
2. **Only modify eight-sleep-local** - All implementation work happens here
3. **Sequential documentation** - Each new markdown file is numbered (00_, 01_, etc.)
4. **Append-only approach** - Once a markdown file is created, we don't modify it. Updates go in the current/new file

## Target Features (from README "In Progress / Help Wanted")

1. **Adjusting Temperatures** - Allow users to set target temperatures for left/right sides
2. **Snoozing and Stopping Alarms** - Control alarm vibrations
3. **Exposing health metrics** - (Waiting for upstream go ahead)

## Documentation Files Structure

| File | Purpose |
|------|---------|
| `00_initial_instructions.md` | This file - project overview and constraints |
| `01_projects_structure.md` | Analysis of both projects' code structure |
| `02_new_required_features.md` | Detailed feature requirements based on free-sleep API |
| `03_implementation_plan.md` | Step-by-step implementation plan |

## Reference Projects

- **eight-sleep-local**: Home Assistant custom integration (target for modifications)
  - Location: `./eight-sleep-local/`
  - Type: Home Assistant HACS integration
  - Language: Python

- **free-sleep**: Local control server for Eight Sleep pods (reference only)
  - Location: `./free-sleep/`
  - Type: Node.js Express server + React app
  - Language: TypeScript
  - API Base: `http://<POD_IP>:3000/api/`

## Key API Endpoints (from free-sleep)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/deviceStatus` | GET | Fetch device status (already implemented) |
| `/api/deviceStatus` | POST | Update device status (temperature, on/off, alarm clear) |
| `/api/alarm` | POST | Execute alarm (vibration) |
| `/api/execute` | POST | Send raw commands to device |
| `/api/metrics/vitals` | GET | Heart rate, HRV, breathing rate |
| `/api/metrics/sleep` | GET | Sleep intervals |

## Next Steps

1. Document detailed project structures in `01_projects_structure.md`
2. Define feature requirements in `02_new_required_features.md`
3. Create implementation plan in `03_implementation_plan.md`
