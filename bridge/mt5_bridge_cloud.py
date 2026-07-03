"""
MT5 Bridge — Cloud Mode
========================
Same as mt5_bridge.py but connects to your cloud relay server
instead of running a local WebSocket server.

Use this when your chart is hosted on GitHub Pages / Vercel
and your relay is on Railway / Render.

USAGE:
  python mt5_bridge_cloud.py

CONFIG:
  Set RELAY_URL to your Railway/Render WebSocket URL.
  Set API_SECRET to match what's in relay_server.py.
"""

import asyncio
import json
import time
import ssl
import MetaTrader5 as mt5
import websockets

# ── Config ───────────────────────────────────────────
RELAY_URL   = "wss://xauusd-terminal-production.up.railway.app"
API_SECRET  = "xauusd-secret-2026"
SYMBOLS     = ["XAUUSDm","EURUSDm","GBPUSDm","USDJPYm","USDCHFm","AUDUSDm","USDCADm"]
TICK_INTERVAL = 0.1
# ─────────────────────────────────────────────────────

def init_mt5():
    if not mt5.initialize():
        print(f"[ERROR] MT5 init failed: {mt5.last_error()}")
        return False
    print(f"[MT5] Connected — {mt5.terminal_info().name}")
    return True

def get_tick(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    info = mt5.symbol_info(symbol)
    return {
        "type":   "tick",
        "symbol": symbol,
        "bid":    round(tick.bid, 5),
        "ask":    round(tick.ask, 5),
        "last":   round(tick.last, 5),
        "volume": tick.volume,
        "spread": round((tick.ask - tick.bid) * (10 ** (info.digits if info else 5)), 1),
        "time":   tick.time,
    }

def get_rates(symbol, timeframe_str, count=100):
    tf_map = {
        "1m": mt5.TIMEFRAME_M1, "5m": mt5.TIMEFRAME_M5,
        "15m": mt5.TIMEFRAME_M15, "1h": mt5.TIMEFRAME_H1,
        "2h": mt5.TIMEFRAME_H2,  "4h": mt5.TIMEFRAME_H4,
        "1d": mt5.TIMEFRAME_D1,
    }
    tf = tf_map.get(timeframe_str, mt5.TIMEFRAME_M15)
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None:
        return []
    return [{"time": int(r["time"]), "open": round(float(r["open"]), 5),
             "high": round(float(r["high"]), 5), "low": round(float(r["low"]), 5),
             "close": round(float(r["close"]), 5), "vol": int(r["tick_volume"])} for r in rates]

async def run():
    if not init_mt5():
        return
    print(f"[RELAY] Connecting to {RELAY_URL} ...")
    last_ticks = {}

    # SSL context that skips certificate verification
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    while True:
        try:
            async with websockets.connect(RELAY_URL, ssl=ssl_ctx) as ws:
                # Identify as feeder
                await ws.send(json.dumps({"role": "feeder", "secret": API_SECRET}))
                print(f"[RELAY] Connected as feeder.")

                # Send initial history
                for sym in SYMBOLS:
                    for tf in ["1m","5m","15m","1h","4h","1d"]:
                        rates = get_rates(sym, tf, 100)
                        if rates:
                            await ws.send(json.dumps({"type":"history","symbol":sym,"tf":tf,"bars":rates}))
                            await asyncio.sleep(0.02)

                async def tick_loop():
                    while True:
                        for sym in SYMBOLS:
                            tick = get_tick(sym)
                            if tick:
                                prev = last_ticks.get(sym)
                                if not prev or prev["bid"] != tick["bid"]:
                                    last_ticks[sym] = tick
                                    await ws.send(json.dumps(tick))
                        await asyncio.sleep(TICK_INTERVAL)

                # Handle incoming requests from charts
                async def recv_loop():
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                            if msg.get("type") == "subscribe":
                                sym = msg.get("symbol","XAUUSDm")
                                tf  = msg.get("tf","15m")
                                rates = get_rates(sym, tf, 100)
                                await ws.send(json.dumps({"type":"history","symbol":sym,"tf":tf,"bars":rates}))
                        except Exception:
                            pass

                await asyncio.gather(tick_loop(), recv_loop())

        except Exception as e:
            print(f"[RELAY] Disconnected: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        mt5.shutdown()
        print("\n[MT5] Stopped.")
