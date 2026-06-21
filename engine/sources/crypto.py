"""crypto.py — live crypto market data from CoinGecko (free, no key required)."""
from __future__ import annotations
from typing import List, Dict

from .http import get
from .. import config


def markets(per_page: int = 50) -> List[Dict]:
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd", "order": "market_cap_desc", "per_page": per_page,
        "page": 1, "sparkline": "true", "price_change_percentage": "24h,7d,30d",
    }
    headers = {}
    if config.COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = config.COINGECKO_API_KEY
    rows = get(url, params=params, headers=headers or None, timeout=25).json()
    out = []
    for c in rows:
        if c.get("id") in config.STABLES:
            continue
        spark = (c.get("sparkline_in_7d") or {}).get("price") or []
        if len(spark) < 24:
            continue
        out.append(c)
    return out
