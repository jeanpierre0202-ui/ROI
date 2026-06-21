"""
prices.py — daily close+volume history for equities.
Primary provider: Tiingo (free token; authenticates per-token so it works from
cloud/CI, unlike Stooq/Yahoo which throttle by IP). Falls back to Stooq.
Returns (closes, volumes, source_url), oldest -> newest.
"""
from __future__ import annotations
import csv
import io
import os
import time
from datetime import date, timedelta
from typing import List, Tuple

from .http import get
from .. import config

TIINGO_API_KEY = os.getenv("TIINGO_API_KEY", "").strip()


def _tiingo(ticker: str) -> Tuple[List[float], List[float], str]:
    start = (date.today() - timedelta(days=220)).isoformat()
    url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
    params = {"startDate": start, "token": TIINGO_API_KEY, "format": "json"}
    r = get(url, params=params, headers={"Content-Type": "application/json"}, timeout=25)
    rows = r.json()
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"tiingo: no data for {ticker}")
    rows = sorted(rows, key=lambda x: x.get("date", ""))
    closes, vols = [], []
    for x in rows:
        c = x.get("adjClose", x.get("close"))
        if c is None:
            continue
        closes.append(float(c))
        vols.append(float(x.get("adjVolume", x.get("volume", 0)) or 0))
    if len(closes) < 30:
        raise RuntimeError(f"tiingo: thin history for {ticker}")
    return closes, vols, "https://www.tiingo.com/"


def _stooq(ticker: str) -> Tuple[List[float], List[float], str]:
    sym = ticker.lower() + ".us"
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    r = get(url, timeout=20)
    text = r.text.strip()
    if not text or text.lower().startswith("<"):
        raise RuntimeError(f"stooq: no data for {ticker}")
    rows = list(csv.DictReader(io.StringIO(text)))
    closes, vols = [], []
    for row in rows:
        try:
            closes.append(float(row.get("Close") or row.get("close")))
            vols.append(float(row.get("Volume") or row.get("volume") or 0))
        except (TypeError, ValueError):
            continue
    if len(closes) < 30:
        raise RuntimeError(f"stooq: thin history for {ticker}")
    return closes, vols, url


def history(ticker: str) -> Tuple[List[float], List[float], str]:
    if TIINGO_API_KEY:
        return _tiingo(ticker)
    return _stooq(ticker)
