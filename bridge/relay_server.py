"""
Cloud WebSocket Relay Server
============================
Deploy this to Railway or Render (free tier).
Your local MT5 bridge connects TO this server,
and your GitHub Pages chart connects FROM this server.

Architecture:
  MT5 (your PC) → mt5_bridge.py → [this relay] ← chart (GitHub Pages)

DEPLOY TO RAILWAY:
  1. Create account at railway.app
  2. New Project → Deploy from GitHub repo
  3. Point to this file as the start command:
     python relay_server.py

DEPLOY TO RENDER:
  1. Create account at render.com
  2. New Web Service → connect GitHub repo
  3. Start command: python relay_server.py
  4. Free tier is fine.

INSTALL:
  pip install websockets
"""

import asyncio
import json
import logging
import os
import websockets

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger(__name__)

PORT       = int(os.environ.get("PORT", 8765))
API_SECRET = os.environ.get("API_SECRET", "xauusd-secret-change-me")

# Clients: browser chart connections
chart_clients = set()
# Feeders: mt5_bridge connections
feeder_clients = set()

async def broadcast_to_charts(message: str):
    dead = set()
    for ws in chart_clients:
        try:
            await ws.send(message)
        except websockets.ConnectionClosed:
            dead.add(ws)
    chart_clients -= dead

async def handle_connection(websocket, path=None):
    # First message determines role
    try:
        first = await asyncio.wait_for(websocket.recv(), timeout=10)
        msg = json.loads(first)
    except (asyncio.TimeoutError, json.JSONDecodeError, websockets.ConnectionClosed):
        await websocket.close()
        return

    role = msg.get("role", "chart")

    if role == "feeder" and msg.get("secret") == API_SECRET:
        # This is the MT5 bridge connecting
        feeder_clients.add(websocket)
        log.info(f"MT5 feeder connected. Total feeders: {len(feeder_clients)}")
        try:
            async for raw in websocket:
                # Forward all MT5 data to chart clients
                await broadcast_to_charts(raw)
        except websockets.ConnectionClosed:
            pass
        finally:
            feeder_clients.discard(websocket)
            log.info(f"MT5 feeder disconnected. Total feeders: {len(feeder_clients)}")

    else:
        # This is a chart browser connecting
        chart_clients.add(websocket)
        log.info(f"Chart client connected. Total charts: {len(chart_clients)}")
        # Send status
        await websocket.send(json.dumps({
            "type":    "status",
            "feeders": len(feeder_clients),
            "live":    len(feeder_clients) > 0,
        }))
        try:
            async for raw in websocket:
                # Forward chart requests to feeders (e.g. subscribe, dom requests)
                for feeder in feeder_clients:
                    try:
                        await feeder.send(raw)
                    except websockets.ConnectionClosed:
                        pass
        except websockets.ConnectionClosed:
            pass
        finally:
            chart_clients.discard(websocket)
            log.info(f"Chart client disconnected. Total charts: {len(chart_clients)}")

async def main():
    log.info("=" * 50)
    log.info("  XAUUSD Order Flow — Cloud Relay Server")
    log.info("=" * 50)
    log.info(f"Listening on port {PORT}")
    log.info(f"API_SECRET: {API_SECRET[:8]}...")
    log.info("Waiting for MT5 bridge and chart connections...")

    async with websockets.serve(handle_connection, "0.0.0.0", PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
