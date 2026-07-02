# XAUUSD Order Flow Terminal — Setup Guide

## Project Structure

```
xauusd-terminal/
├── frontend/
│   └── index.html          ← your chart (deploy to GitHub Pages)
├── bridge/
│   ├── mt5_bridge.py       ← LOCAL mode: runs on your PC
│   ├── mt5_bridge_cloud.py ← CLOUD mode: runs on your PC, connects to relay
│   ├── relay_server.py     ← deploy to Railway/Render
│   ├── requirements.txt    ← for mt5_bridge.py
│   └── requirements_relay.txt ← for relay_server.py
└── .github/
    └── workflows/
        └── deploy.yml      ← auto-deploys frontend to GitHub Pages
```

---

## PHASE 1 — Run Locally (Test First)

### Step 1 — Install Python
1. Go to https://python.org/downloads
2. Download Python 3.11 or newer
3. During install: CHECK "Add Python to PATH"
4. Verify: open Command Prompt → type `python --version`

### Step 2 — Install Python packages
Open Command Prompt and run:
```
pip install MetaTrader5 websockets
```

### Step 3 — Make sure MT5 is open
- Open your MetaTrader 5 terminal
- Log in to your broker account
- Make sure XAUUSD is in your Market Watch

### Step 4 — Run the bridge
```
cd path\to\xauusd-terminal\bridge
python mt5_bridge.py
```
You should see:
```
[MT5] Connected — MetaTrader 5
[WS] Starting server on ws://localhost:8765
[WS] Streaming: XAUUSD, EURUSD, GBPUSD...
```

### Step 5 — Open the chart
Open `frontend/index.html` in your browser.
The green dot in the top-right should say **LIVE**.

---

## PHASE 2 — Deploy to GitHub Pages (Share Online)

### Step 1 — Create GitHub account
Go to https://github.com and sign up (free).

### Step 2 — Create a new repository
1. Click "New repository"
2. Name it: `xauusd-terminal`
3. Set to **Public**
4. Click "Create repository"

### Step 3 — Upload your files
Option A — GitHub Desktop (easier):
1. Download https://desktop.github.com
2. Clone your new repo
3. Copy all files from `xauusd-terminal/` into the cloned folder
4. Commit and Push

Option B — Command line:
```
cd xauusd-terminal
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/xauusd-terminal.git
git push -u origin main
```

### Step 4 — Enable GitHub Pages
1. Go to your repo on GitHub
2. Settings → Pages
3. Source: **GitHub Actions**
4. The workflow in `.github/workflows/deploy.yml` will auto-deploy

### Step 5 — Your chart URL
After deploy (takes ~1 min):
```
https://YOUR_USERNAME.github.io/xauusd-terminal/
```

---

## PHASE 3 — Cloud Relay (Real-Time Data from Anywhere)

This lets your GitHub Pages chart receive REAL MT5 data
even though GitHub Pages can't run a server.

### Step 1 — Deploy relay to Railway (free)
1. Go to https://railway.app → sign up with GitHub
2. New Project → Deploy from GitHub repo
3. Select your `xauusd-terminal` repo
4. Set root directory to: `bridge`
5. Start command: `python relay_server.py`
6. Add environment variable:
   - `API_SECRET` = `your-secret-password-here`
7. Railway gives you a URL like:
   `your-app.railway.app`

### Step 2 — Update your bridge config
Open `bridge/mt5_bridge_cloud.py` and set:
```python
RELAY_URL  = "wss://your-app.railway.app"
API_SECRET = "your-secret-password-here"
```

### Step 3 — Update your chart config
Open `frontend/index.html` and find this line near the top of the script:
```javascript
const WS_URL = 'ws://localhost:8765';
```
Change it to:
```javascript
const WS_URL = 'wss://your-app.railway.app';
```
Push to GitHub — it auto-deploys.

### Step 4 — Run cloud bridge on your PC
```
python mt5_bridge_cloud.py
```
This runs on YOUR PC (where MT5 is), connects to Railway,
and your online chart gets live data.

---

## Final Architecture

```
YOUR PC
  MT5 Terminal
      ↓
  mt5_bridge_cloud.py
      ↓ (wss)
RAILWAY/RENDER
  relay_server.py
      ↓ (wss)
ANYWHERE IN THE WORLD
  github.io/xauusd-terminal  ← live chart
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| MT5 init failed | Make sure MT5 is open and logged in |
| `pip` not found | Reinstall Python with "Add to PATH" checked |
| Chart shows DISCONNECTED | Check mt5_bridge.py is running |
| No XAUUSD data | Add XAUUSD to MT5 Market Watch |
| Railway deploy fails | Check start command is `python relay_server.py` and root is `bridge/` |

---

## Quick Reference

| File | What it does | Where it runs |
|------|-------------|---------------|
| `mt5_bridge.py` | Local bridge | Your PC |
| `mt5_bridge_cloud.py` | Cloud bridge | Your PC |
| `relay_server.py` | WebSocket relay | Railway/Render |
| `frontend/index.html` | The chart | GitHub Pages |
