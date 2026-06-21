"""
prices.py — daily close+volume history for equities.

Default provider is Stooq (no API key, reliable CSV). Alpha Vantage is supported
if you set ALPHAVANTAGE_API_KEY (note its free tier is heavily rate-limited).
Returns (closes, volumes, source_url), oldest -> newest.
"""
from __future__ import annotations
import csv
import io
import time
from typing import List, Tuple

from .http import get
from .. import config


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


def _alphavantage(ticker: str) -> Tuple[List[float], List[float], str]:
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_DAILY", "symbol": ticker,
        "outputsize": "compact", "apikey": config.ALPHAVANTAGE_API_KEY,
    }
    r = get(url, params=params, timeout=25)
    data = r.json()
    series = data.get("Time Series (Daily)")
    if not series:
        raise RuntimeError(f"alphavantage: {data.get('Note') or data.get('Information') or 'no data'}")
    items = sorted(series.items())
    closes = [float(v["4. close"]) for _, v in items]
    vols = [float(v.get("5. volume", 0)) for _, v in items]
    time.sleep(13)  # respect free-tier rate limit
    return closes, vols, url + f"?symbol={ticker}"


def history(ticker: str) -> Tuple[List[float], List[float], str]:
    if config.PRICE_PROVIDER == "alphavantage" and config.ALPHAVANTAGE_API_KEY:
        return _alphavantage(ticker)
    return _stooq(ticker)
