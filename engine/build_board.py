"""
build_board.py — ROI's nightly brain.

Pulls real data from every connector, computes transparent scores, ranks the
equity and crypto boards, THEN triangulates each name across sources (quant,
gov flows, global news, social) into a consensus/conviction read, and writes a
full AI dossier for the top names. Output: board.json.

Run:  python -m engine.build_board
"""
from __future__ import annotations
import json
import os
import time
import traceback
from datetime import datetime, timezone
from statistics import mean
from typing import Dict, List

from . import config, synthesis
from .indicators import score_series
from .sources import prices, fred, edgar, congress, crypto, news, reddit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATHS = [os.path.join(ROOT, "data", "board.json"),
             os.path.join(ROOT, "web", "public", "board.json")]

DISCLAIMER = ("ROI is an information and research tool, not a broker, adviser, or "
              "fiduciary. Nothing here is a recommendation to buy or sell any security "
              "or asset. Markets carry real risk of loss. Verify with primary sources "
              "and a licensed professional before acting.")
fred_sources: List[Dict] = []


def _pctile(value, sorted_vals) -> float:
    if not sorted_vals:
        return 50.0
    return sum(1 for v in sorted_vals if v <= value) / len(sorted_vals) * 100.0


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


def _thesis(name, sc, flow_note, catalyst_note) -> str:
    ch = sc["changes"]
    trend = "uptrend" if ch["d30"] > 3 else "downtrend" if ch["d30"] < -3 else "range-bound"
    rsi = sc["rsi"]
    rsi_state = "overbought" if rsi >= 70 else "oversold" if rsi <= 30 else "neutral"
    vol_word = "low" if sc["volatility"] < 25 else "elevated" if sc["volatility"] < 45 else "high"
    bits = [f"{trend} (30d {ch['d30']:+.1f}%)", f"RSI {rsi:.0f} ({rsi_state})", f"{vol_word} volatility"]
    extra = "; ".join([x for x in (flow_note, catalyst_note) if x])
    return f"{name}: {', '.join(bits)}{' — ' + extra if extra else ''}."


def _triggers(sc) -> Dict[str, str]:
    lv = sc["levels"]
    return {
        "buy": f"Add on pullbacks toward the 30-day pivot ${lv['pivot']:,.2f}; stronger entry near support ${lv['support']:,.2f}.",
        "hold": f"Hold while price stays above the pivot ${lv['pivot']:,.2f} and RSI holds the 40-68 band (now {sc['rsi']:.0f}).",
        "sell": f"Trim if RSI runs above 72 or price closes below support ${lv['support']:,.2f} on rising volume.",
    }


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


def build_equities(cong: Dict, fil: Dict) -> Dict:
    uni = config.universe()
    rows, dollar_vol = [], {}
    print(f"[equities] universe of {len(uni)} names via {config.PRICE_PROVIDER if not os.getenv('TIINGO_API_KEY') else 'tiingo'}")
    for tkr, sector in uni.items():
        try:
            closes, vols, src = prices.history(tkr)
        except Exception as e:
            print(f"  ! {tkr}: {e}")
            continue
        recent = list(zip(closes[-20:], vols[-20:]))
        dollar_vol[tkr] = mean([c * v for c, v in recent]) if recent else 0.0
        rows.append({"tkr": tkr, "sector": sector, "closes": closes, "src": src})
        time.sleep(0.3)
    if not rows:
        return {"long": [], "short": []}
    dv_sorted = sorted(dollar_vol.values())
    enriched = []
    for row in rows:
        tkr = row["tkr"]
        sc = score_series(row["closes"], _pctile(dollar_vol.get(tkr, 0), dv_sorted))
        c = cong.get(tkr, {})
        flow_note = congress.signal_note(c)
        cat_note = edgar.catalyst_note(fil.get(tkr, []))
        sources = [{"title": "Daily price history", "url": row["src"]}]
        if c.get("source"):
            sources.append(c["source"])
        for f in fil.get(tkr, [])[:1]:
            sources.append({"title": f"SEC {f['form']} ({f['date']})", "url": f["filing_url"]})
        if fred_sources:
            sources.append(fred_sources[0])
        enriched.append({
            "name": config.company_name(tkr), "ticker": tkr, "sector": row["sector"],
            "price": sc["price"], "rsi": sc["rsi"], "volatility": sc["volatility"],
            "changes": sc["changes"], "levels": sc["levels"], "components": sc["components"],
            "signal_long": sc["signal_long"], "signal_short": sc["signal_short"],
            "security": sc["security"], "risk": _risk_band(sc["security"], sc["volatility"]),
            "spark": _downsample(row["closes"][-60:]),
            "thesis": _thesis(config.company_name(tkr), sc, flow_note, cat_note),
            **_triggers(sc), "flow_note": flow_note, "catalyst_note": cat_note, "sources": sources,
        })
    return {"long": _rank(enriched, "signal_long"), "short": _rank(enriched, "signal_short")}


def build_crypto() -> Dict:
    try:
        coins = crypto.markets(per_page=50)
    except Exception as e:
        print(f"[crypto] feed error: {e}")
        return {"long": [], "short": []}
    n = len(coins)
    enriched = []
    for i, c in enumerate(coins):
        spark = c["sparkline_in_7d"]["price"]
        sc = score_series(spark, (n - i) / n * 100.0)
        sc["price"] = c["current_price"]
        sec = config.crypto_sector(c["id"])
        enriched.append({
            "name": c["name"], "ticker": (c.get("symbol") or "").upper(), "sector": sec,
            "price": c["current_price"], "rsi": sc["rsi"], "volatility": sc["volatility"],
            "changes": {"d1": round(c.get("price_change_percentage_24h_in_currency") or 0, 2),
                        "d7": round(c.get("price_change_percentage_7d_in_currency") or 0, 2),
                        "d30": round(c.get("price_change_percentage_30d_in_currency") or 0, 2)},
            "levels": sc["levels"], "components": sc["components"],
            "signal_long": sc["signal_long"], "signal_short": sc["signal_short"],
            "security": sc["security"], "risk": _risk_band(sc["security"], sc["volatility"]),
            "spark": _downsample(spark), "thesis": _thesis(c["name"], sc, "", ""),
            **_triggers(sc), "flow_note": "", "image": c.get("image"),
            "sources": [{"title": "CoinGecko market data", "url": f"https://www.coingecko.com/en/coins/{c['id']}"}],
        })
    return {"long": _rank(enriched, "signal_long"), "short": _rank(enriched, "signal_short")}


def _news_query(item, kind) -> str:
    return f'"{config.company_name(item["ticker"])}" stock' if kind == "equity" else f'{item["name"]} crypto'


def _dedup_sources(item):
    seen, out = set(), []
    for s in item.get("sources", []):
        u = s.get("url")
        if u and u not in seen:
            seen.add(u)
            out.append(s)
    item["sources"] = out


def enrich(equities: Dict, crypto_board: Dict):
    """Triangulate every board name across sources; AI-dossier the top names."""
    entries = []
    for horizon in ("long", "short"):
        for it in equities.get(horizon, []):
            entries.append((it, "equity", horizon))
        for it in crypto_board.get(horizon, []):
            entries.append((it, "crypto", horizon))
    if not entries:
        return

    news_cache, social_cache = {}, {}
    print(f"[synthesis] consensus over {len({it['ticker'] for it,_,_ in entries})} unique names")
    for it, kind, horizon in entries:
        t = it["ticker"]
        if t not in news_cache:
            try:
                news_cache[t] = news.coverage(_news_query(it, kind))
            except Exception:
                news_cache[t] = {"available": False, "tone": 0, "volume": 0, "countries": [], "headlines": []}
            time.sleep(0.5)
        if t not in social_cache:
            try:
                social_cache[t] = reddit.sentiment(it.get("name") or t)
            except Exception:
                social_cache[t] = {"available": False, "direction": 0, "mentions": 0}
        nv, sv = news_cache[t], social_cache[t]
        it["consensus"] = synthesis.consensus(it, horizon, it.get("flow_note", ""), nv, sv)
        it["news"] = {k: nv.get(k) for k in ("available", "tone", "volume", "countries", "headlines")}
        if nv.get("source"):
            it.setdefault("sources", []).append(nv["source"])
        if sv.get("available") and sv.get("source"):
            it.setdefault("sources", []).append(sv["source"])

    # full AI dossier for the top unique names (cost control via SYNTHESIS_MAX_NAMES)
    best_rank, kind_of, name_of = {}, {}, {}
    for it, kind, horizon in entries:
        t = it["ticker"]
        best_rank[t] = min(best_rank.get(t, 99), it.get("rank", 99))
        kind_of[t], name_of[t] = kind, it.get("name") or t
    ordered = sorted(best_rank, key=lambda t: best_rank[t])[:config.SYNTHESIS_MAX_NAMES]
    prov = config.active_provider()
    if prov != "none" and ordered:
        print(f"[synthesis] AI dossiers for top {len(ordered)} names via {prov}")
    dossier_cache = {}
    for t in ordered:
        rep = next((it for it, k, h in entries if it["ticker"] == t), None)
        if not rep:
            continue
        kind = "US-listed equity" if kind_of[t] == "equity" else "cryptocurrency"
        d = synthesis.dossier(name_of[t], t, kind, rep, rep.get("consensus", {}),
                              rep.get("flow_note", ""), news_cache.get(t, {}), social_cache.get(t, {}))
        if d:
            dossier_cache[t] = d

    for it, kind, horizon in entries:
        if it["ticker"] in dossier_cache:
            it["dossier"] = dossier_cache[it["ticker"]]
            for s in it["dossier"].get("sources", []):
                if s.get("url"):
                    it.setdefault("sources", []).append(s)
        _dedup_sources(it)


def main():
    started = time.time()
    print("=== ROI board build ===", datetime.now(timezone.utc).isoformat())
    print(f"[diag] provider={config.active_provider()} gemini_key={bool(config.GEMINI_API_KEY)} "
          f"tiingo_key={bool(os.getenv('TIINGO_API_KEY'))} max_names={config.SYNTHESIS_MAX_NAMES}")
    macro = {"available": False}
    try:
        macro = fred.macro()
        if macro.get("sources"):
            fred_sources.extend(macro["sources"])
    except Exception:
        traceback.print_exc()
    cong = {}
    try:
        _t = time.time(); cong = congress.recent_trades(days=60)
        print(f"[congress] {len(cong)} tickers with recent disclosures ({time.time()-_t:.0f}s)")
    except Exception:
        traceback.print_exc()
    fil = {}
    try:
        _t = time.time(); fil = edgar.recent_filings(list(config.universe().keys()), days=30)
        print(f"[edgar] {len(fil)} tickers with recent filings ({time.time()-_t:.0f}s)")
    except Exception:
        traceback.print_exc()

    _t = time.time(); equities = build_equities(cong, fil); print(f"[equities] built ({time.time()-_t:.0f}s)")
    _t = time.time(); crypto_board = build_crypto(); print(f"[crypto] built ({time.time()-_t:.0f}s)")
    try:
        _t = time.time(); enrich(equities, crypto_board); print(f"[synthesis] enriched ({time.time()-_t:.0f}s)")
    except Exception:
        traceback.print_exc()

    board = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "macro": macro, "equities": equities, "crypto": crypto_board,
        "disclaimer": DISCLAIMER,
        "provenance": {
            "prices": "tiingo" if os.getenv("TIINGO_API_KEY") else config.PRICE_PROVIDER,
            "macro": "FRED" if macro.get("available") else "unavailable",
            "filings": "SEC EDGAR", "congress": "House/Senate Stock Watcher (community)",
            "crypto": "CoinGecko", "news": "GDELT global",
            "synthesis": config.active_provider() if config.active_provider() != "none" else "consensus-only (no AI key)",
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
