"""
reddit.py — optional social sentiment from Reddit.

Uses the official API via app credentials (free). If REDDIT_CLIENT_ID/SECRET
are not set, this cleanly returns "unavailable" and the engine leans on GDELT
+ the AI layer for social signal instead. No fabrication when keys are absent.
"""
from __future__ import annotations
import time
from typing import Dict

import requests

from .. import config

_token = {"value": None, "exp": 0}
SUBS = "wallstreetbets+stocks+investing+cryptocurrency"

# crude lexicon for a transparent, rule-based sentiment tilt
_POS = {"buy", "bull", "bullish", "moon", "long", "calls", "up", "rally", "breakout", "undervalued", "gem"}
_NEG = {"sell", "bear", "bearish", "short", "puts", "down", "dump", "crash", "overvalued", "rug", "avoid"}


def _auth():
    if not (config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET):
        return None
    if _token["value"] and time.time() < _token["exp"] - 60:
        return _token["value"]
    try:
        r = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(config.REDDIT_CLIENT_ID, config.REDDIT_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": config.REDDIT_USER_AGENT}, timeout=20,
        )
        r.raise_for_status()
        j = r.json()
        _token["value"] = j["access_token"]
        _token["exp"] = time.time() + j.get("expires_in", 3600)
        return _token["value"]
    except Exception:
        return None


def sentiment(query: str) -> Dict:
    tok = _auth()
    if not tok:
        return {"available": False, "direction": 0, "mentions": 0}
    try:
        r = requests.get(
            f"https://oauth.reddit.com/r/{SUBS}/search",
            params={"q": query, "sort": "new", "limit": 25, "t": "week", "restrict_sr": "true"},
            headers={"User-Agent": config.REDDIT_USER_AGENT, "Authorization": f"bearer {tok}"},
            timeout=20,
        )
        r.raise_for_status()
        posts = r.json().get("data", {}).get("children", [])
    except Exception:
        return {"available": False, "direction": 0, "mentions": 0}
    pos = neg = 0
    for p in posts:
        text = (p.get("data", {}).get("title", "") + " " +
                p.get("data", {}).get("selftext", "")).lower()
        words = set(text.split())
        pos += len(words & _POS)
        neg += len(words & _NEG)
    total = pos + neg
    direction = 0
    if total >= 3:
        ratio = (pos - neg) / total
        direction = 1 if ratio > 0.2 else -1 if ratio < -0.2 else 0
    return {"available": len(posts) > 0, "direction": direction,
            "mentions": len(posts), "pos": pos, "neg": neg,
            "source": {"title": "Reddit (WSB/stocks/crypto)", "url": "https://www.reddit.com/"}}
