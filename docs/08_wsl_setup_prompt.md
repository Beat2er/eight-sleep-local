# WSL Setup Prompt for LLM

Copy this prompt to another LLM session to set up and run the free-sleep server in WSL.

---

## Prompt

```
I need help setting up and running a Node.js server in WSL for local development testing.

## Project Context

This is the "free-sleep" project - a local server that normally runs on an Eight Sleep pod device. I want to run it locally in WSL to test a Home Assistant integration without the actual hardware.

## Project Location

The project is at:
- Windows path: C:\Users\Felix\PycharmProjects\freesleep_combo\free-sleep\server
- WSL path: /mnt/c/Users/Felix/PycharmProjects/freesleep_combo/free-sleep/server

## What I Need You To Do

1. **Navigate to the project** in WSL

2. **Check/install Node.js 24** (project uses Volta with Node 24.11.0)
   - Install volta if needed: `curl https://get.volta.sh | bash`
   - Or use nvm if preferred

3. **Update `.env.local`** file with these contents:
   ```
   ENV="local"
   DATA_FOLDER="./free-sleep-data/"
   DATABASE_URL="file:./free-sleep-data/free-sleep.db"
   ```

4. **Create the data directory** if it doesn't exist:
   ```bash
   mkdir -p free-sleep-data/lowdb
   ```

5. **Install dependencies:**
   ```bash
   npm install
   ```

6. **Generate Prisma client:**
   ```bash
   npm run generate:local
   ```

7. **Run the dev server:**
   ```bash
   npm run dev:local
   ```

8. **Verify it's working** by testing an endpoint:
   ```bash
   curl http://localhost:3000/api/services
   ```

## Expected Result

- Server running at http://localhost:3000
- Can access from Windows browser at same URL (WSL2 port forwarding)

## If deviceStatus endpoint fails

That's expected - it needs actual hardware. The server should still start and other endpoints like /api/services, /api/presence, /api/schedules should work.

## Optional: Add mock deviceStatus

If you want the /api/deviceStatus GET endpoint to work, you can modify:
`src/routes/deviceStatus/deviceStatus.ts`

Add mock data return when in dev mode (check `config.remoteDevMode`).

## Troubleshooting

- If prisma fails, try: `npx prisma generate`
- If port 3000 is in use, check what's using it: `lsof -i :3000`
- If npm install fails, delete node_modules and package-lock.json, try again

Let me know when the server is running or if you hit any issues!
```

---

## Additional Context (if needed)

The server is an Express.js TypeScript application that:
- Runs on port 3000
- Uses lowdb (JSON file storage) for schedules/settings
- Uses SQLite (via Prisma) for health metrics
- In `remoteDevMode` (ENV=local), skips connecting to actual pod hardware

Key files:
- `src/server.ts` - Main entry point
- `src/config.ts` - Detects dev mode from ENV variable
- `src/routes/` - All API endpoints
- `.env.local` - Local development environment variables
