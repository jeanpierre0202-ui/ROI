"""
fred.py — macro regime from the St. Louis Fed (FRED). Needs FRED_API_KEY (free).

Pulls a small, decision-relevant set of series and derives a plain-English
regime read: rates path, curve shape, inflation trend, risk appetite.
"""
from __future__ import annotations
from typing import Dict, List

from .http import get
from .. import config

SERIES = {
    "DGS10": "10-yr Treasury",
    "DGS2": "2-yr Treasury",
    "T10Y2Y": "10y–2y spread",
    "FEDFUNDS": "Fed funds rate",
    "CPIAUCSL": "CPI (index)",
    "UNRATE": "Unemployment",
    "VIXCLS": "VIX",
    "DTWEXBGS": "USD (broad)",
    "DCOILWTICO": "WTI crude",
}


def _latest_two(series_id: str):
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id, "api_key": config.FRED_API_KEY,
        "file_type": "json", "sort_order": "desc", "limit": 6,
    }
    r = get(url, params=params, timeout=20)
    obs = [o for o in r.json().get("observations", []) if o.get("value") not in (".", None, "")]
    vals = []
    for o in obs:
        try:
            vals.append(float(o["value"]))
        except ValueError:
            pass
    return vals[:2] if vals else []


def macro() -> Dict:
    if not config.FRED_API_KEY:
        return {"available": False, "reason": "FRED_API_KEY not set",
                "metrics": [], "regime": "unknown", "summary": "", "watch": [], "sources": []}
    metrics: List[Dict] = []
    snap: Dict[str, float] = {}
    for sid, label in SERIES.items():
        try:
            vals = _latest_two(sid)
            if not vals:
                continue
            cur = vals[0]
            prev = vals[1] if len(vals) > 1 else cur
            snap[sid] = cur
            metrics.append({"id": sid, "label": label, "value": cur,
                            "delta": round(cur - prev, 3)})
        except Exception:
            continue

    curve = snap.get("T10Y2Y")
    vix = snap.get("VIXCLS")
    ff = snap.get("FEDFUNDS")
    parts = []
    if curve is not None:
        parts.append("inverted yield curve" if curve < 0 else "positive yield curve")
    if vix is not None:
        parts.append("calm risk appetite" if vix < 18 else
                      "elevated volatility" if vix < 28 else "stressed volatility")
    if ff is not None:
        parts.append(f"policy rate near {ff:.2f}%")
    regime = "restrictive / late-cycle" if (curve is not None and curve < 0) else "expansion-leaning"
    summary = ("Macro read from FRED: " + ", ".join(parts) + ".") if parts else "FRED data sparse."
    watch = []
    if curve is not None and curve < 0:
        watch.append("Curve un-inversion can precede slowdown")
    if vix is not None and vix >= 22:
        watch.append("Volatility elevated — size positions smaller")
    watch.append("Next CPI / FOMC print is the swing factor")

    return {
        "available": True, "regime": regime, "summary": summary,
        "metrics": metrics, "watch": watch[:3],
        "sources": [{"title": "FRED (St. Louis Fed)", "url": "https://fred.stlouisfed.org/"}],
    }
