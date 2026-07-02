import asyncio
import json
import time
import MetaTrader5 as mt5
import websockets

SYMBOLS = ["XAUUSDm", "EURUSDm", "GBPUSDm", "USDJPYm", "USDCHFm", "AUDUSDm", "USDCADm"]
WS_HOST = "0.0.0.0"
WS_PORT = 8765
TICK_INTERVAL = 0.05  # 20 ticks/sec for accuracy

connected_clients = set()

# ── Real tick store ──────────────────────────────────
# For each symbol+tf+bar_time → {buy, sell, levels:{price:{buy,sell}}}
tick_store = {}  # symbol_tf_bartime -> {buy, sell, vol, levels:{price:{buy,sell}}}

# Last tick per symbol to detect direction
last_tick_data = {}

# Current bar time per symbol+tf
current_bar_time = {}

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
    """Floor timestamp to bar open time"""
    s = TF_SECONDS.get(tf, 900)
    return (ts // s) * s

def classify_tick(symbol, tick):
    """
    Classify tick as BUY or SELL:
    - If last price == ask → aggressive buyer hit the ask → BUY
    - If last price == bid → aggressive seller hit the bid → SELL
    - If last == 0 → use price movement direction
    """
    prev = last_tick_data.get(symbol)
    bid = tick.bid
    ask = tick.ask
    last = tick.last

    side = None
    if last > 0:
        # Most accurate: compare last to bid/ask
        spread = ask - bid
        if spread > 0:
            mid = (bid + ask) / 2
            if last >= mid:
                side = "buy"
            else:
                side = "sell"
        else:
            side = "buy"
    elif prev:
        # Fallback: price movement direction
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
    """Record tick into all timeframes"""
    price = tick.last if tick.last > 0 else (tick.bid + tick.ask) / 2
    price_level = round(round(price / 0.05) * 0.05, 2)
    vol = max(1, int(tick.volume_real) if tick.volume_real > 0 else 1)

    for tf in TF_SECONDS:
        bar_t = get_bar_time(tick.time, tf)
        key = f"{symbol}_{tf}_{bar_t}"
        # Initialize if not exists
        if key not in tick_store:
            tick_store[key] = {"buy": 0, "sell": 0, "vol": 0, "bar_time": bar_t, "levels": {}}
        store = tick_store[key]
        if side == "buy":
            store["buy"] += vol
        else:
            store["sell"] += vol
        store["vol"] += vol
        store["bar_time"] = bar_t
        # Record level
        pl = str(price_level)
        if pl not in store["levels"]:
            store["levels"][pl] = {"buy": 0, "sell": 0}
        if side == "buy":
            store["levels"][pl]["buy"] += vol
        else:
            store["levels"][pl]["sell"] += vol

def get_tick_data(symbol, tf, bar_time):
    """Get accumulated tick data for a bar"""
    key = f"{symbol}_{tf}_{bar_time}"
    return tick_store.get(key, None)

def init_mt5():
    if not mt5.initialize():
        print(f"[ERROR] MT5 initialize() failed: {mt5.last_error()}")
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
        # Check if we have real tick data for this bar
        td = get_tick_data(symbol, timeframe_str, bar_t)
        total_vol = int(r["tick_volume"])
        isBull = float(r["close"]) >= float(r["open"])

        if td and td["vol"] > 0:
            # REAL tick data available
            buy_vol  = td["buy"]
            sell_vol = td["sell"]
            delta    = buy_vol - sell_vol
            levels   = [
                {"price": float(p), "buy": v["buy"], "sell": v["sell"]}
                for p, v in sorted(td["levels"].items(), key=lambda x: float(x[0]))
            ]
        else:
            # Estimate from OHLC (historical bars)
            pr = float(r["high"]) - float(r["low"])
            body = abs(float(r["close"]) - float(r["open"]))
            body_pct = body / pr if pr > 0 else 0.5
            dominance = 0.50 + body_pct * 0.18
            buy_vol  = int(total_vol * (dominance if isBull else 1-dominance))
            sell_vol = total_vol - buy_vol
            delta    = buy_vol - sell_vol if isBull else -(sell_vol - buy_vol)
            # Build estimated levels
            step = 0.05
            steps = max(4, int(pr / step)) if pr > 0 else 4
            levels = []
            for i in range(steps + 1):
                p = round(float(r["low"]) + (pr / steps) * i, 2) if steps > 0 else float(r["close"])
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
            "open":    float(round(r["open"],  2)),
            "high":    float(round(r["high"],  2)),
            "low":     float(round(r["low"],   2)),
            "close":   float(round(r["close"], 2)),
            "vol":     total_vol,
            "buyVol":  buy_vol,
            "sellVol": sell_vol,
            "delta":   delta,
            "levels":  levels,
            "real":    td is not None and td["vol"] > 0,
        })
    return result

async def broadcast(message):
    if not connected_clients:
        return
    data = json.dumps(message)
    dead = set()
    for ws in list(connected_clients):
        try:
            await ws.send(data)
        except Exception:
            dead.add(ws)
    for ws in dead:
        connected_clients.discard(ws)

async def handle_client(websocket, path=None):
    connected_clients.add(websocket)
    print(f"[WS] Client connected — total: {len(connected_clients)}")
    try:
        # Send history for all symbols
        for sym in SYMBOLS:
            for tf in ["1m", "5m", "15m", "1h", "4h", "1d"]:
                rates = get_rates(sym, tf, 200)
                if rates:
                    try:
                        await websocket.send(json.dumps({
                            "type":   "history",
                            "symbol": sym,
                            "tf":     tf,
                            "bars":   rates,
                        }))
                    except Exception:
                        return
                    await asyncio.sleep(0.02)

        async for raw in websocket:
            try:
                msg = json.loads(raw)
                if msg.get("type") == "subscribe":
                    sym = msg.get("symbol", "XAUUSDm")
                    tf  = msg.get("tf", "15m")
                    rates = get_rates(sym, tf, 200)
                    if rates:
                        await websocket.send(json.dumps({
                            "type":   "history",
                            "symbol": sym,
                            "tf":     tf,
                            "bars":   rates,
                        }))
            except Exception:
                pass
    except websockets.exceptions.ConnectionClosedError:
        pass  # Normal browser disconnect - ignore silently
    except websockets.exceptions.ConnectionClosedOK:
        pass  # Clean disconnect
    except Exception as e:
        if 'close frame' not in str(e).lower():
            print(f"[WS] Error: {e}")
    finally:
        connected_clients.discard(websocket)
        print(f"[WS] Client disconnected — total: {len(connected_clients)}")

async def tick_streamer():
    """Stream real ticks, classify BUY/SELL, broadcast updates"""
    prev_ticks = {}
    bar_broadcast_time = {}

    print("[TICK] Real tick recorder started — classifying BUY/SELL...")

    while True:
        try:
            for sym in SYMBOLS:
                result = get_tick(sym)
                if result is None:
                    continue
                tick_dict, raw_tick = result

                prev = prev_ticks.get(sym)
                bid_changed = not prev or prev["bid"] != tick_dict["bid"]
                ask_changed = not prev or prev["ask"] != tick_dict["ask"]

                if bid_changed or ask_changed:
                    # Classify this tick
                    side = classify_tick(sym, raw_tick)
                    tick_dict["side"] = side

                    # Record into tick store
                    record_tick(sym, raw_tick, side)

                    # Update last tick
                    last_tick_data[sym] = {
                        "bid": raw_tick.bid,
                        "ask": raw_tick.ask,
                        "side": side,
                    }
                    prev_ticks[sym] = tick_dict

                    # Broadcast tick with side classification
                    await broadcast(tick_dict)

                    # Every 2 seconds, broadcast updated bar data for current TF
                    now = time.time()
                    last_bc = bar_broadcast_time.get(sym, 0)
                    if now - last_bc > 2.0:
                        bar_broadcast_time[sym] = now
                        for tf in ["1m", "5m", "15m", "1h", "4h", "1d"]:
                            rates = get_rates(sym, tf, 5)  # last 5 bars only
                            if rates:
                                await broadcast({
                                    "type":   "bar_update",
                                    "symbol": sym,
                                    "tf":     tf,
                                    "bars":   rates,
                                })

        except Exception as e:
            print(f"[TICK] Error: {e}")

        await asyncio.sleep(TICK_INTERVAL)

async def main():
    print("=" * 55)
    print("  XAUUSD Order Flow — MT5 Real Tick Bridge v2")
    print("=" * 55)
    if not init_mt5():
        print("[ERROR] Could not connect to MT5.")
        return
    print(f"[WS]   Server: ws://localhost:{WS_PORT}")
    print(f"[TICK] Symbols: {', '.join(SYMBOLS)}")
    print(f"[TICK] Real BUY/SELL classification: ENABLED")
    print("  Open chart: http://localhost:3000")
    print("  Press Ctrl+C to stop")
    print("=" * 55)
    async with websockets.serve(
        handle_client, WS_HOST, WS_PORT,
        ping_interval=20,
        ping_timeout=10,
        close_timeout=5,
        max_size=10_000_000,
    ):
        await tick_streamer()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[MT5] Bridge stopped.")
        mt5.shutdown()
