"""
congress.py — congressional (STOCK Act) trade disclosures.

HONEST NOTE: the authoritative sources are the House Clerk and Senate eFD
portals, which publish PDFs that are painful to parse at scale. This connector
uses the well-known community-maintained JSON mirrors (House/Senate Stock
Watcher). Those mirrors are free but can go stale or offline. If they fail,
the engine simply proceeds without congressional signal rather than guessing.

For production reliability, swap in a maintained API (e.g. Quiver Quantitative,
Capitol Trades, Unusual Whales) by reimplementing `recent_trades()`.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from .http import get

HOUSE = "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"
SENATE = "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/aggregate/all_transactions.json"


def _parse_date(s: str):
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def recent_trades(days: int = 60) -> Dict[str, Dict]:
    """Returns ticker -> {buys, sells, last_date, chamber, source}."""
    cutoff = datetime.utcnow().date() - timedelta(days=days)
    agg: Dict[str, Dict] = defaultdict(lambda: {"buys": 0, "sells": 0, "last_date": None, "chamber": set()})

    for url, chamber in ((HOUSE, "House"), (SENATE, "Senate")):
        try:
            rows = get(url, timeout=30).json()
        except Exception:
            continue
        for row in rows:
            tkr = (row.get("ticker") or "").strip().upper()
            if not tkr or tkr in ("--", "N/A"):
                continue
            d = _parse_date(row.get("transaction_date") or row.get("transactionDate") or "")
            if not d or d < cutoff:
                continue
            ttype = (row.get("type") or row.get("transaction_type") or "").lower()
            rec = agg[tkr]
            if "purchase" in ttype or "buy" in ttype:
                rec["buys"] += 1
            elif "sale" in ttype or "sell" in ttype:
                rec["sells"] += 1
            rec["chamber"].add(chamber)
            if rec["last_date"] is None or d > rec["last_date"]:
                rec["last_date"] = d

    out = {}
    for tkr, rec in agg.items():
        if rec["buys"] == 0 and rec["sells"] == 0:
            continue
        out[tkr] = {
            "buys": rec["buys"], "sells": rec["sells"],
            "last_date": rec["last_date"].isoformat() if rec["last_date"] else None,
            "chamber": ", ".join(sorted(rec["chamber"])),
            "source": {"title": "House/Senate Stock Watcher",
                       "url": "https://www.capitoltrades.com/"},
        }
    return out


def signal_note(rec: Dict) -> str:
    if not rec:
        return ""
    b, s = rec["buys"], rec["sells"]
    if b > s and b >= 2:
        return f"{rec['chamber']} net buying ({b} buys / {s} sells, last {rec['last_date']})"
    if s > b and s >= 2:
        return f"{rec['chamber']} net selling ({s} sells / {b} buys, last {rec['last_date']})"
    if b or s:
        return f"{rec['chamber']} activity ({b} buys / {s} sells)"
    return ""
