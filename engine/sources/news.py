"""
news.py — global news + tone via GDELT (free, no API key).

GDELT indexes worldwide news in 100+ languages and scores article "tone".
We use it for two honest signals per asset:
  • tone   -> average sentiment of recent coverage (news direction)
  • volume -> how much the world is talking about it (attention)
  • countries / headlines -> geographic spread + sourced links
This is our backbone for the "worldwide news / geopolitical / social" layer.
"""
from __future__ import annotations
from typing import Dict
from collections import Counter

from .http import get

BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
UA = {"User-Agent": "roi-research/1.0 (+https://github.com)"}


def _artlist(query: str, timespan: str = "7d", maxrecords: int = 15):
    params = {"query": query, "mode": "ArtList", "maxrecords": str(maxrecords),
              "timespan": timespan, "format": "json", "sort": "datedesc"}
    r = get(BASE, params=params, headers=UA, timeout=25)
    try:
        return r.json().get("articles", []) or []
    except Exception:
        return []


def _tone(query: str, timespan: str = "14d") -> float:
    params = {"query": query, "mode": "TimelineTone", "timespan": timespan, "format": "json"}
    r = get(BASE, params=params, headers=UA, timeout=25)
    try:
        series = r.json().get("timeline", [])
        if not series:
            return 0.0
        data = series[0].get("data", [])
        vals = [d.get("value") for d in data if isinstance(d.get("value"), (int, float))]
        return round(sum(vals) / len(vals), 2) if vals else 0.0
    except Exception:
        return 0.0


def coverage(query: str) -> Dict:
    """Returns {available, tone, volume, countries, headlines:[{title,url,domain,country}]}."""
    try:
        arts = _artlist(query)
    except Exception:
        arts = []
    try:
        tone = _tone(query)
    except Exception:
        tone = 0.0
    if not arts and tone == 0.0:
        return {"available": False, "tone": 0.0, "volume": 0, "countries": [], "headlines": []}
    countries = [a.get("sourcecountry") for a in arts if a.get("sourcecountry")]
    top_countries = [c for c, _ in Counter(countries).most_common(5)]
    headlines = [{"title": a.get("title", "")[:160], "url": a.get("url", ""),
                  "domain": a.get("domain", ""), "country": a.get("sourcecountry", "")}
                 for a in arts[:6] if a.get("url")]
    return {
        "available": True,
        "tone": tone,                  # negative = bearish coverage, positive = bullish
        "volume": len(arts),           # attention proxy
        "countries": top_countries,    # geographic spread
        "headlines": headlines,
        "source": {"title": "GDELT global news", "url": "https://www.gdeltproject.org/"},
    }
