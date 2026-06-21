"""
edgar.py — recent SEC filings per ticker (official, free).

Surfaces near-term catalysts: 8-K (material events), Form 4 (insider trades),
10-Q/10-K. SEC requires a descriptive User-Agent with a contact — set
SEC_USER_AGENT. Returns a map ticker -> list of recent notable filings.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List

from .http import get
from .. import config

NOTABLE = {"8-K", "4", "10-Q", "10-K"}
_cik_cache: Dict[str, str] = {}


def _headers():
    return {"User-Agent": config.SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"}


def _load_cik_map():
    if _cik_cache:
        return _cik_cache
    try:
        r = get("https://www.sec.gov/files/company_tickers.json", headers=_headers(), timeout=25)
        for _, row in r.json().items():
            _cik_cache[row["ticker"].upper()] = str(row["cik_str"]).zfill(10)
    except Exception:
        pass
    return _cik_cache


def recent_filings(tickers: List[str], days: int = 30) -> Dict[str, List[Dict]]:
    out: Dict[str, List[Dict]] = {}
    cmap = _load_cik_map()
    if not cmap:
        return out
    cutoff = datetime.utcnow().date() - timedelta(days=days)
    for t in tickers:
        cik = cmap.get(t.upper().replace("-", "."))  # BRK-B -> BRK.B style
        if not cik:
            cik = cmap.get(t.upper())
        if not cik:
            continue
        try:
            r = get(f"https://data.sec.gov/submissions/CIK{cik}.json",
                    headers=_headers(), timeout=25)
            recent = r.json().get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accns = recent.get("accessionNumber", [])
            hits = []
            for form, date, accn in zip(forms, dates, accns):
                if form not in NOTABLE:
                    continue
                try:
                    d = datetime.strptime(date, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if d < cutoff:
                    continue
                accn_nodash = accn.replace("-", "")
                hits.append({
                    "form": form, "date": date,
                    "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form}",
                    "filing_url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn_nodash}/{accn}-index.htm",
                })
            if hits:
                out[t.upper()] = hits[:6]
        except Exception:
            continue
    return out


def catalyst_note(filings: List[Dict]) -> str:
    if not filings:
        return ""
    forms = {f["form"] for f in filings}
    bits = []
    if "4" in forms:
        bits.append("insider Form 4 activity")
    if "8-K" in forms:
        bits.append("recent 8-K event")
    if "10-Q" in forms or "10-K" in forms:
        bits.append("fresh financials filed")
    return "; ".join(bits)
