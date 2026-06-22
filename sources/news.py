"""
news.py — global news + tone via GDELT (free, no key).

Cloud-hardened: short timeouts, single attempt, short-circuits when GDELT is
unreachable so it never hangs the build. GDELT throttles datacenter IPs, so we
fail fast and let the rest of the engine carry on.
"""
from __future__ import annotations
from typing import Dict
from collections import Counter

import requests

BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
UA = {"User-Agent": "roi-research/1.0 (+https://github.com)"}
TIMEOUT = 6  # short on purpose; one attempt, no retries


def _gdelt(params):
    try:
        r = requests.get(BASE, params=params, headers=UA, timeout=TIMEOUT)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _tone_from(data) -> float:
    try:
        series = (data or {}).get("timeline", [])
        if not series:
            return 0.0
        rows = series[0].get("data", [])
        vals = [x.get("value") for x in rows if isinstance(x.get("value"), (int, float))]
        return round(sum(vals) / len(vals), 2) if vals else 0.0
    except Exception:
        return 0.0


def coverage(query: str) -> Dict:
    empty = {"available": False, "tone": 0.0, "volume": 0, "countries": [], "headlines": []}
    art = _gdelt({"query": query, "mode": "ArtList", "maxrecords": "15",
                  "timespan": "7d", "format": "json", "sort": "datedesc"})
    arts = (art or {}).get("articles", []) or []
    if not arts:
        return empty  # GDELT down / no coverage -> bail fast, skip the 2nd call
    tone_data = _gdelt({"query": query, "mode": "TimelineTone", "timespan": "14d", "format": "json"})
    tone = _tone_from(tone_data)
    countries = [a.get("sourcecountry") for a in arts if a.get("sourcecountry")]
    top_countries = [c for c, _ in Counter(countries).most_common(5)]
    headlines = [{"title": a.get("title", "")[:160], "url": a.get("url", ""),
                  "domain": a.get("domain", ""), "country": a.get("sourcecountry", "")}
                 for a in arts[:6] if a.get("url")]
    return {"available": True, "tone": tone, "volume": len(arts),
            "countries": top_countries, "headlines": headlines,
            "source": {"title": "GDELT global news", "url": "https://www.gdeltproject.org/"}}
