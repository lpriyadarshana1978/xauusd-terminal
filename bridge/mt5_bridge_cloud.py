"""
MT5 Bridge — Cloud Mode (Full Footprint)
==========================================
Connects to your cloud relay server with full tick classification,
footprint levels, and delta data — same quality as the local bridge.

USAGE:
  python mt5_bridge_cloud.py
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
TICK_INTERVAL = 0.05  # 20 ticks/sec for accuracy
# ─────────────────────────────────────────────────────

# ── Real tick store ──────────────────────────────────
tick_store = {}
last_tick_data = {}

# Cache each symbol's true decimal precision from MT5 itself (2 for XAU, 3 for JPY pairs,
# 5 for majors like EURUSD) instead of assuming gold's 2-decimal precision everywhere.
_digits_cache = {}
def get_digits(symbol):
    if symbol not in _digits_cache:
        info = mt5.symbol_info(symbol)
        _digits_cache[symbol] = info.digits if info else 2
    return _digits_cache[symbol]

def get_price_step(symbol):
    # A footprint bucket of "5 points" scaled to the symbol's own precision.
    # For XAU (2 digits) this reproduces the original 0.05 step exactly.
    # For EURUSD (5 digits) it becomes 0.00005; for USDJPY (3 digits) it becomes 0.005.
    return 5 * (10 ** -get_digits(symbol))

TF_SECONDS = {
    "1m":  60,
    "5m":  300,
    "15m": 900,
    "1h":  3600,
    "2h":  7200,
    "4h":  14400,
    "1d":  86400,
}

def get_bar_time(ts, tf):
    s = TF_SECONDS.get(tf, 900)
    return (ts // s) * s

def classify_tick(symbol, tick):
    prev = last_tick_data.get(symbol)
    bid = tick.bid
    ask = tick.ask
    last = tick.last
    side = None
    if last > 0:
        spread = ask - bid
        if spread > 0:
            mid = (bid + ask) / 2
            side = "buy" if last >= mid else "sell"
        else:
            side = "buy"
    elif prev:
        prev_mid = (prev["bid"] + prev["ask"]) / 2
        curr_mid = (bid + ask) / 2
        if curr_mid > prev_mid:
            side = "buy"
        elif curr_mid < prev_mid:
            side = "sell"
        else:
            side = prev.get("side", "buy")
    else:
        side = "buy"
    return side

def record_tick(symbol, tick, side):
    price = tick.last if tick.last > 0 else (tick.bid + tick.ask) / 2
    step = get_price_step(symbol)
    price_level = round(round(price / step) * step, get_digits(symbol))
    vol = max(1, int(tick.volume_real) if tick.volume_real > 0 else 1)
    for tf in TF_SECONDS:
        bar_t = get_bar_time(tick.time, tf)
        key = f"{symbol}_{tf}_{bar_t}"
        if key not in tick_store:
            tick_store[key] = {"buy": 0, "sell": 0, "vol": 0, "bar_time": bar_t, "levels": {}}
        store = tick_store[key]
        if side == "buy":
            store["buy"] += vol
        else:
            store["sell"] += vol
        store["vol"] += vol
        store["bar_time"] = bar_t
        pl = str(price_level)
        if pl not in store["levels"]:
            store["levels"][pl] = {"buy": 0, "sell": 0}
        if side == "buy":
            store["levels"][pl]["buy"] += vol
        else:
            store["levels"][pl]["sell"] += vol

def get_tick_data(symbol, tf, bar_time):
    key = f"{symbol}_{tf}_{bar_time}"
    return tick_store.get(key, None)

def init_mt5():
    if not mt5.initialize():
        print(f"[ERROR] MT5 init failed: {mt5.last_error()}")
        return False
    info = mt5.terminal_info()
    print(f"[MT5] Connected — {info.name} build {info.build}")
    return True

def get_tick(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    info = mt5.symbol_info(symbol)
    digits = info.digits if info else 2
    spread = round((tick.ask - tick.bid) * (10 ** digits), 1)
    return {
        "type":   "tick",
        "symbol": symbol,
        "bid":    round(tick.bid, digits),
        "ask":    round(tick.ask, digits),
        "last":   round(tick.last, digits),
        "volume": tick.volume,
        "volume_real": tick.volume_real,
        "spread": spread,
        "time":   tick.time,
        "time_msc": tick.time_msc,
    }, tick

def get_rates(symbol, timeframe_str, count=200):
    tf_map = {
        "1m":  mt5.TIMEFRAME_M1,
        "5m":  mt5.TIMEFRAME_M5,
        "15m": mt5.TIMEFRAME_M15,
        "1h":  mt5.TIMEFRAME_H1,
        "2h":  mt5.TIMEFRAME_H2,
        "4h":  mt5.TIMEFRAME_H4,
        "1d":  mt5.TIMEFRAME_D1,
    }
    tf = tf_map.get(timeframe_str, mt5.TIMEFRAME_M15)
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None:
        return []
    result = []
    for r in rates:
        bar_t = int(r["time"])
        td = get_tick_data(symbol, timeframe_str, bar_t)
        total_vol = int(r["tick_volume"])
        isBull = float(r["close"]) >= float(r["open"])
        digits = get_digits(symbol)

        if td and td["vol"] > 0:
            buy_vol  = td["buy"]
            sell_vol = td["sell"]
            delta    = buy_vol - sell_vol
            raw_levels = list(td["levels"].items())
            if len(raw_levels) > 40:
                # Keep the 40 highest-volume price levels rather than letting a long-lived bar
                # (a 1d bar stays "current" for up to 24h) accumulate unbounded distinct levels.
                raw_levels.sort(key=lambda x: x[1]["buy"] + x[1]["sell"], reverse=True)
                raw_levels = raw_levels[:40]
            levels = [
                {"price": float(p), "buy": v["buy"], "sell": v["sell"]}
                for p, v in sorted(raw_levels, key=lambda x: float(x[0]))
            ]
        else:
            pr = float(r["high"]) - float(r["low"])
            body = abs(float(r["close"]) - float(r["open"]))
            body_pct = body / pr if pr > 0 else 0.5
            dominance = 0.50 + body_pct * 0.18
            buy_vol  = int(total_vol * (dominance if isBull else 1-dominance))
            sell_vol = total_vol - buy_vol
            delta    = buy_vol - sell_vol if isBull else -(sell_vol - buy_vol)
            step = get_price_step(symbol)
            # Cap at 40 - the frontend already merges footprint rows down to ~20 per candle for
            # display, so anything beyond that is wasted bandwidth. Without this cap, a wide-range
            # bar (a full day's gold range can be $50-100) divided into ~$0.05 steps produced
            # 1,000-2,000 levels for a SINGLE bar - across 100 bars that's what caused the 100+MB
            # payloads and the resulting 1009 "message too big" disconnects.
            steps = max(4, min(40, int(pr / step))) if pr > 0 else 4
            levels = []
            for i in range(steps + 1):
                p = round(float(r["low"]) + (pr / steps) * i, digits) if steps > 0 else float(r["close"])
                dist = abs(p - float(r["close"])) / pr if pr > 0 else 0.5
                w = max(0.1, 1 - dist * 1.8)
                lv = max(1, int((total_vol / steps) * w * 1.5))
                br = 0.45 + 0.15*(p - float(r["low"]))/pr if pr > 0 else 0.5
                br = br if isBull else 1 - br
                levels.append({
                    "price": p,
                    "buy":  max(1, int(lv * br)),
                    "sell": max(1, int(lv * (1-br))),
                    "estimated": True
                })

        result.append({
            "time":    bar_t,
            "open":    float(round(r["open"],  digits)),
            "high":    float(round(r["high"],  digits)),
            "low":     float(round(r["low"],   digits)),
            "close":   float(round(r["close"], digits)),
            "vol":     total_vol,
            "buyVol":  buy_vol,
            "sellVol": sell_vol,
            "delta":   delta,
            "levels":  levels,
            "real":    td is not None and td["vol"] > 0,
        })
    return result

async def run():
    if not init_mt5():
        return

    loop = asyncio.get_event_loop()
    # MT5's Python API is fully synchronous/blocking. Calling it directly inside the asyncio
    # event loop freezes the loop for however long each call takes - during that time the
    # bridge can't respond to the relay's keepalive pings, so the relay concludes the feeder
    # is dead and force-closes with 1011 (ping timeout). Running these calls in a thread pool
    # keeps the event loop free to answer pings while MT5 does its (slow) network I/O.
    async def fetch_rates(sym, tf, count):
        return await loop.run_in_executor(None, get_rates, sym, tf, count)
    async def fetch_tick(sym):
        return await loop.run_in_executor(None, get_tick, sym)

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    prev_ticks = {}
    bar_broadcast_time = {}

    # Diagnostic wrapper: logs which message (symbol/tf/type) is unexpectedly huge, instead of
    # silently hitting the 1009 "message too big" disconnect with no way to tell what caused it.
    async def safe_send(ws, payload, label):
        raw = json.dumps(payload)
        size = len(raw)
        if size > 2_000_000:
            print(f"[SIZE WARNING] {label} is {size:,} bytes - investigate this payload")
        await ws.send(raw)

    print(f"[RELAY] Connecting to {RELAY_URL} ...")
    print(f"[TICK] Real BUY/SELL classification: ENABLED")

    while True:
        try:
            # max_size must match the relay's 50MB limit - otherwise this client falls back to
            # the websockets library default (~1MB) and can itself reject/kill the connection
            # with 1009 (message too big) on a perfectly legitimate larger frame.
            async with websockets.connect(RELAY_URL, ssl=ssl_ctx, max_size=50_000_000) as ws:
                await ws.send(json.dumps({"role": "feeder", "secret": API_SECRET}))
                print(f"[RELAY] Connected as feeder.")

                # Send initial history with full footprint data
                for sym in SYMBOLS:
                    for tf in ["1m","5m","15m","1h","4h","1d"]:
                        rates = await fetch_rates(sym, tf, 300)
                        if rates:
                            await safe_send(ws, {
                                "type":   "history",
                                "symbol": sym,
                                "tf":     tf,
                                "bars":   rates,
                            }, f"initial history {sym}/{tf}")
                            await asyncio.sleep(0.02)

                async def tick_loop():
                    while True:
                        try:
                            for sym in SYMBOLS:
                                result = await fetch_tick(sym)
                                if result is None:
                                    continue
                                tick_dict, raw_tick = result
                                prev = prev_ticks.get(sym)
                                bid_changed = not prev or prev["bid"] != tick_dict["bid"]
                                ask_changed = not prev or prev["ask"] != tick_dict["ask"]

                                if bid_changed or ask_changed:
                                    side = classify_tick(sym, raw_tick)
                                    tick_dict["side"] = side
                                    record_tick(sym, raw_tick, side)
                                    last_tick_data[sym] = {
                                        "bid": raw_tick.bid,
                                        "ask": raw_tick.ask,
                                        "side": side,
                                    }
                                    prev_ticks[sym] = tick_dict
                                    await ws.send(json.dumps(tick_dict))

                                    now = time.time()
                                    last_bc = bar_broadcast_time.get(sym, 0)
                                    if now - last_bc > 2.0:
                                        bar_broadcast_time[sym] = now
                                        for tf in ["1m","5m","15m","1h","4h","1d"]:
                                            rates = await fetch_rates(sym, tf, 5)
                                            if rates:
                                                await safe_send(ws, {
                                                    "type":   "bar_update",
                                                    "symbol": sym,
                                                    "tf":     tf,
                                                    "bars":   rates,
                                                }, f"bar_update {sym}/{tf}")
                        except Exception as e:
                            print(f"[TICK] Error: {e}")
                        await asyncio.sleep(TICK_INTERVAL)

                async def recv_loop():
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                            if msg.get("type") == "subscribe":
                                sym = msg.get("symbol","XAUUSDm")
                                tf  = msg.get("tf","15m")
                                rates = await fetch_rates(sym, tf, 300)
                                if rates:
                                    await safe_send(ws, {
                                        "type":   "history",
                                        "symbol": sym,
                                        "tf":     tf,
                                        "bars":   rates,
                                    }, f"subscribe history {sym}/{tf}")
                        except Exception as e:
                            print(f"[RECV] Error: {e}")

                await asyncio.gather(tick_loop(), recv_loop())

        except Exception as e:
            print(f"[RELAY] Disconnected: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        print("=" * 55)
        print("  XAUUSD Order Flow — MT5 Cloud Bridge (Full Footprint)")
        print("=" * 55)
        asyncio.run(run())
    except KeyboardInterrupt:
        mt5.shutdown()
        print("\n[MT5] Stopped.")
