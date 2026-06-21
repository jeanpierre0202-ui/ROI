"""http.py — one polite, resilient GET used by every connector."""
from __future__ import annotations
import time
import requests

_session = requests.Session()


def get(url, *, headers=None, params=None, timeout=20, retries=3, backoff=1.6):
    last = None
    for attempt in range(retries):
        try:
            r = _session.get(url, headers=headers, params=params, timeout=timeout)
            if r.status_code == 200:
                return r
            last = RuntimeError(f"HTTP {r.status_code} for {url}")
        except requests.RequestException as e:
            last = e
        time.sleep(backoff ** attempt)
    if last:
        raise last
    raise RuntimeError(f"failed: {url}")
