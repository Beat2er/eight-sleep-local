# 09 - WSL Node.js Server Setup

Complete guide for setting up and running the free-sleep Node.js server in WSL for local development testing.

---

## Project Location

- **Windows:** `C:\Users\Felix\PycharmProjects\freesleep_combo\free-sleep\server`
- **WSL:** `/mnt/c/Users/Felix/PycharmProjects/freesleep_combo/free-sleep/server`

---

## Setup Steps

### 1. Navigate to Project Directory

```bash
cd /mnt/c/Users/Felix/PycharmProjects/freesleep_combo/free-sleep/server
```

### 2. Install Node.js 24 via Volta

```bash
# Install Volta
curl https://get.volta.sh | bash

# Set up Volta paths for current session
export VOLTA_HOME="$HOME/.volta"
export PATH="$VOLTA_HOME/bin:$PATH"

# Install Node.js 24
volta install node@24

# Verify installation
node --version  # Should output: v24.x.x
npm --version   # Should output: 11.x.x
```

### 3. Create Environment Configuration

Create `.env.local` file with local development settings:

```bash
cat > .env.local << 'EOF'
ENV="local"
DATA_FOLDER="./free-sleep-data/"
DATABASE_URL="file:./free-sleep-data/free-sleep.db"
EOF
```

### 4. Create Data Directory Structure

```bash
mkdir -p free-sleep-data/lowdb
```

### 5. Install Dependencies

```bash
# Make sure Volta paths are set
export VOLTA_HOME="$HOME/.volta"
export PATH="$VOLTA_HOME/bin:$PATH"

# Install npm packages
npm install
```

### 6. Generate Prisma Client

```bash
npm run generate:local
```

### 7. Start Development Server

```bash
npm run dev:local
```

The server will run at `http://localhost:3000` and will be accessible from both WSL and Windows.

---

## Running Server in Background

To run the server in the background (useful for long-running sessions):

```bash
# Start server in background
nohup npm run dev:local > server.log 2>&1 &

# Check if it's running
ps aux | grep node

# View logs
tail -f server.log

# Stop the server
pkill -f "node.*server.ts"
```

---

## Testing the Server

### Test API Endpoints

```bash
# Test services endpoint
curl http://localhost:3000/api/services

# Expected response:
# {"sentryLogging":{"enabled":false},"biometrics":{...}}

# Test presence endpoint (may need mock data)
curl http://localhost:3000/api/presence

# Test schedules endpoint
curl http://localhost:3000/api/schedules

# Test settings endpoint
curl http://localhost:3000/api/settings
```

### Available Endpoints in Dev Mode

| Endpoint | Method | Works in Dev? | Notes |
|----------|--------|---------------|-------|
| `/api/services` | GET/POST | ✅ | Full functionality |
| `/api/schedules` | GET/POST | ✅ | Full functionality |
| `/api/settings` | GET/POST | ✅ | Full functionality |
| `/api/presence` | GET | ✅ | Returns default/stored values |
| `/api/metrics/vitals` | GET | ✅ | Needs seeded data |
| `/api/metrics/sleep` | GET | ✅ | Needs seeded data |
| `/api/deviceStatus` | GET | ❌ | Requires hardware |
| `/api/deviceStatus` | POST | ❌ | Requires hardware |

---

## Troubleshooting

### Volta Command Not Found

If `volta` command is not found after installation:

```bash
# Add to your ~/.bashrc or ~/.zshrc
export VOLTA_HOME="$HOME/.volta"
export PATH="$VOLTA_HOME/bin:$PATH"

# Reload shell configuration
source ~/.bashrc
```

### Port Already in Use

If port 3000 is already in use:

```bash
# Find process using port 3000
lsof -i :3000

# Kill the process
kill -9 <PID>

# Or use a different port
PORT=3001 npm run dev:local
```

### Permission Issues

If you encounter permission issues:

```bash
# Fix npm permissions
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
export PATH=~/.npm-global/bin:$PATH
```

---

## Next Steps

1. **Add Mock Data:** Consider adding mock responses for `/api/deviceStatus` endpoint for testing the Home Assistant integration
2. **Seed Database:** Add test data to SQLite for testing health metrics endpoints
3. **Test HA Integration:** Configure Home Assistant to connect to `http://localhost:3000`

---

## Notes

- The server runs in `remoteDevMode` when `ENV=local`, which skips hardware initialization
- All API routes are available but device-specific endpoints return errors without hardware
- Data is stored locally in `./free-sleep-data/` directory
- WSL2 automatically forwards localhost ports to Windows