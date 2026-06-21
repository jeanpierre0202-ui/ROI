"""
build_board.py — ROI's nightly brain.

Pulls real data from every connector, computes transparent scores, ranks the
equity and crypto boards (long & short horizons), writes board.json.

Run:  python -m engine.build_board
Output: data/board.json  and  web/public/board.json
"""
from __future__ import annotations
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from statistics import mean
from typing import Dict, List

from . import config
from .indicators import score_series, clamp
from .sources import prices, fred, edgar, congress, crypto

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATHS = [os.path.join(ROOT, "data", "board.json"),
             os.path.join(ROOT, "web", "public", "board.json")]

DISCLAIMER = ("ROI is an information and research tool, not a broker, adviser, or "
              "fiduciary. Nothing here is a recommendation to buy or sell any security "
              "or asset. Markets carry real risk of loss. Verify with primary sources "
              "and a licensed professional before acting.")


def _pctile(value, sorted_vals) -> float:
    if not sorted_vals:
        return 50.0
    below = sum(1 for v in sorted_vals if v <= value)
    return below / len(sorted_vals) * 100.0


def _risk_band(security: int, vol: float) -> str:
    if security >= 66 and vol < 35:
        return "low"
    if security >= 45:
        return "med"
    return "high"


def _downsample(arr: List[float], n: int = 40) -> List[float]:
    if len(arr) <= n:
        return [round(x, 6) for x in arr]
    step = len(arr) / n
    return [round(arr[int(i * step)], 6) for i in range(n)]


def _thesis(name, sec, sc, flow_note, catalyst_note) -> str:
    ch = sc["changes"]
    trend = "uptrend" if ch["d30"] > 3 else "downtrend" if ch["d30"] < -3 else "range-bound"
    rsi = sc["rsi"]
    rsi_state = "overbought" if rsi >= 70 else "oversold" if rsi <= 30 else "neutral"
    vol_word = "low" if sc["volatility"] < 25 else "elevated" if sc["volatility"] < 45 else "high"
    bits = [f"{trend} (30d {ch['d30']:+.1f}%)", f"RSI {rsi:.0f} ({rsi_state})", f"{vol_word} volatility"]
    extra = "; ".join([x for x in (flow_note, catalyst_note) if x])
    tail = f" — {extra}" if extra else ""
    return f"{name}: {', '.join(bits)}{tail}."


def _triggers(sc) -> Dict[str, str]:
    lv = sc["levels"]
    return {
        "buy": f"Add on pullbacks toward the 30-day pivot ${lv['pivot']:,.2f}; stronger entry near support ${lv['support']:,.2f}.",
        "hold": f"Hold while price stays above the pivot ${lv['pivot']:,.2f} and RSI holds the 40–68 band (now {sc['rsi']:.0f}).",
        "sell": f"Trim if RSI runs above 72 or price closes below support ${lv['support']:,.2f} on rising volume.",
    }


# ----------------------------- EQUITIES ------------------------------------
def build_equities(cong: Dict, fil: Dict) -> Dict:
    uni = config.universe()
    rows = []
    dollar_vol = {}
    print(f"[equities] universe of {len(uni)} names via {config.PRICE_PROVIDER}")
    for tkr, sector in uni.items():
        try:
            closes, vols, src = prices.history(tkr)
        except Exception as e:
            print(f"  ! {tkr}: {e}")
            continue
        recent = list(zip(closes[-20:], vols[-20:]))
        dv = mean([c * v for c, v in recent]) if recent else 0.0
        dollar_vol[tkr] = dv
        rows.append({"tkr": tkr, "sector": sector, "closes": closes, "src": src})
        time.sleep(0.4)  # be polite

    if not rows:
        return {"long": [], "short": [], "note": "no equity data available"}

    dv_sorted = sorted(dollar_vol.values())
    enriched = []
    for row in rows:
        tkr = row["tkr"]
        depth = _pctile(dollar_vol.get(tkr, 0), dv_sorted)
        sc = score_series(row["closes"], depth)
        c = cong.get(tkr, {})
        flow_note = congress.signal_note(c)
        cat_note = edgar.catalyst_note(fil.get(tkr, []))
        sources = [{"title": "Stooq price history", "url": row["src"]}]
        if c.get("source"):
            sources.append(c["source"])
        for f in fil.get(tkr, [])[:1]:
            sources.append({"title": f"SEC {f['form']} ({f['date']})", "url": f["filing_url"]})
        if fred_sources:
            sources.append(fred_sources[0])
        enriched.append({
            "name": tkr, "ticker": tkr, "sector": row["sector"],
            "price": sc["price"], "rsi": sc["rsi"], "volatility": sc["volatility"],
            "changes": sc["changes"], "levels": sc["levels"], "components": sc["components"],
            "signal_long": sc["signal_long"], "signal_short": sc["signal_short"],
            "security": sc["security"], "action": sc["action"], "action_tone": sc["action_tone"],
            "risk": _risk_band(sc["security"], sc["volatility"]),
            "spark": _downsample(row["closes"][-60:]),
            "thesis": _thesis(tkr, row["sector"], sc, flow_note, cat_note),
            **_triggers(sc),
            "flow_note": flow_note, "catalyst_note": cat_note,
            "sources": sources,
        })
    return {"long": _rank(enriched, "signal_long"), "short": _rank(enriched, "signal_short")}


# ----------------------------- CRYPTO --------------------------------------
def build_crypto() -> Dict:
    try:
        coins = crypto.markets(per_page=50)
    except Exception as e:
        print(f"[crypto] feed error: {e}")
        return {"long": [], "short": [], "note": "crypto feed unavailable"}
    n = len(coins)
    enriched = []
    for i, c in enumerate(coins):
        spark = c["sparkline_in_7d"]["price"]
        depth = (n - i) / n * 100.0
        sc = score_series(spark, depth)
        sc["price"] = c["current_price"]  # use live price, not last sparkline point
        sec = config.crypto_sector(c["id"])
        enriched.append({
            "name": c["name"], "ticker": (c.get("symbol") or "").upper(), "sector": sec,
            "price": c["current_price"], "rsi": sc["rsi"], "volatility": sc["volatility"],
            "changes": {
                "d1": round(c.get("price_change_percentage_24h_in_currency") or 0, 2),
                "d7": round(c.get("price_change_percentage_7d_in_currency") or 0, 2),
                "d30": round(c.get("price_change_percentage_30d_in_currency") or 0, 2),
            },
            "levels": sc["levels"], "components": sc["components"],
            "signal_long": sc["signal_long"], "signal_short": sc["signal_short"],
            "security": sc["security"], "action": sc["action"], "action_tone": sc["action_tone"],
            "risk": _risk_band(sc["security"], sc["volatility"]),
            "spark": _downsample(spark),
            "thesis": _thesis(c["name"], sec, sc, "", ""),
            **_triggers(sc),
            "image": c.get("image"),
            "sources": [{"title": "CoinGecko market data",
                         "url": f"https://www.coingecko.com/en/coins/{c['id']}"}],
        })
    return {"long": _rank(enriched, "signal_long"), "short": _rank(enriched, "signal_short")}


def _rank(items: List[Dict], key: str) -> List[Dict]:
    ranked = sorted(items, key=lambda x: x[key], reverse=True)[:8]
    crown_ids = {id(x) for x in sorted(ranked, key=lambda x: x["security"], reverse=True)[:3]}
    out = []
    for i, x in enumerate(ranked):
        y = dict(x)
        y["rank"] = i + 1
        y["tier"] = "crown" if id(x) in crown_ids else "core"
        y["signal"] = x[key]
        out.append(y)
    return out


fred_sources: List[Dict] = []


def main():
    started = time.time()
    print("=== ROI board build ===", datetime.now(timezone.utc).isoformat())

    macro = {"available": False}
    try:
        macro = fred.macro()
        if macro.get("sources"):
            fred_sources.extend(macro["sources"])
    except Exception:
        traceback.print_exc()

    cong = {}
    try:
        cong = congress.recent_trades(days=60)
        print(f"[congress] {len(cong)} tickers with recent disclosures")
    except Exception:
        traceback.print_exc()

    fil = {}
    try:
        fil = edgar.recent_filings(list(config.universe().keys()), days=30)
        print(f"[edgar] {len(fil)} tickers with recent filings")
    except Exception:
        traceback.print_exc()

    equities = build_equities(cong, fil)
    crypto_board = build_crypto()

    board = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "macro": macro,
        "equities": equities,
        "crypto": crypto_board,
        "disclaimer": DISCLAIMER,
        "provenance": {
            "prices": config.PRICE_PROVIDER,
            "macro": "FRED" if macro.get("available") else "unavailable",
            "filings": "SEC EDGAR",
            "congress": "House/Senate Stock Watcher (community)",
            "crypto": "CoinGecko",
        },
    }

    for p in OUT_PATHS:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            json.dump(board, f, indent=2)
        print("wrote", p)
    print(f"done in {time.time()-started:.1f}s")


if __name__ == "__main__":
    main()
