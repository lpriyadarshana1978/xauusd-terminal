import asyncio
import json
import logging
import os
import websockets

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger(__name__)

PORT       = int(os.environ.get("PORT", 8765))
API_SECRET = os.environ.get("API_SECRET", "xauusd-secret-change-me")

chart_clients = set()
feeder_clients = set()

async def broadcast_to_charts(message):
    global chart_clients
    dead = set()
    for ws in list(chart_clients):
        try:
            await ws.send(message)
        except Exception:
            dead.add(ws)
    chart_clients -= dead

async def handle_connection(websocket):
    """Handler compatible with websockets 13+"""
    try:
        first = await asyncio.wait_for(websocket.recv(), timeout=10)
        msg = json.loads(first)
    except Exception:
        return

    role = msg.get("role", "chart")

    if role == "feeder" and msg.get("secret") == API_SECRET:
        feeder_clients.add(websocket)
        log.info(f"MT5 feeder connected. Feeders: {len(feeder_clients)}")
        try:
            async for raw in websocket:
                await broadcast_to_charts(raw)
        except websockets.ConnectionClosed:
            pass
        finally:
            feeder_clients.discard(websocket)
            log.info(f"MT5 feeder disconnected. Feeders: {len(feeder_clients)}")
    else:
        chart_clients.add(websocket)
        log.info(f"Chart connected. Charts: {len(chart_clients)}")
        await websocket.send(json.dumps({
            "type": "status",
            "feeders": len(feeder_clients),
            "live": len(feeder_clients) > 0,
        }))
        try:
            async for raw in websocket:
                for feeder in list(feeder_clients):
                    try:
                        await feeder.send(raw)
                    except Exception:
                        pass
        except websockets.ConnectionClosed:
            pass
        finally:
            chart_clients.discard(websocket)
            log.info(f"Chart disconnected. Charts: {len(chart_clients)}")

async def main():
    log.info("=" * 50)
    log.info("  XAUUSD Order Flow - Cloud Relay Server")
    log.info("=" * 50)
    log.info(f"Port: {PORT}")
    log.info(f"API_SECRET: {API_SECRET[:8]}...")
    log.info("Waiting for connections...")

    async with websockets.serve(handle_connection, "0.0.0.0", PORT, max_size=50_000_000, ping_interval=20, ping_timeout=10):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
