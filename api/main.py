"""
api/main.py — serves the latest board and (optionally) rebuilds it on a schedule.

  GET  /api/health      -> ok
  GET  /api/board       -> latest board.json
  POST /api/refresh     -> rebuild now (guard with X-Refresh-Token header)

Two ways to keep it fresh:
  • Static path (recommended): a daily GitHub Action builds board.json and
    commits it; the frontend reads the committed file. You don't need this API.
  • Live API path: run this service and set ROI_AUTO_REFRESH=1 to rebuild in
    a background thread every ROI_REFRESH_HOURS (default 24). Self-contained —
    no separate cron, no shared-disk requirement.
"""
from __future__ import annotations
import json
import os
import threading
import time

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(ROOT, "data", "board.json")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN", "")
AUTO = os.getenv("ROI_AUTO_REFRESH", "") in ("1", "true", "yes")
REFRESH_HOURS = float(os.getenv("ROI_REFRESH_HOURS", "24"))

app = FastAPI(title="ROI Intelligence API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
_lock = threading.Lock()


def _rebuild():
    if not _lock.acquire(blocking=False):
        return False
    try:
        from engine.build_board import main as build
        build()
        return True
    finally:
        _lock.release()


@app.get("/api/health")
def health():
    return {"ok": True, "has_board": os.path.exists(BOARD), "auto_refresh": AUTO}


@app.get("/api/board")
def board():
    if not os.path.exists(BOARD):
        raise HTTPException(503, "board not built yet — POST /api/refresh or wait for the scheduler")
    with open(BOARD) as f:
        return JSONResponse(json.load(f))


@app.post("/api/refresh")
def refresh(x_refresh_token: str = Header(default="")):
    if REFRESH_TOKEN and x_refresh_token != REFRESH_TOKEN:
        raise HTTPException(401, "bad token")
    return {"status": "rebuilt" if _rebuild() else "already running"}


def _scheduler():
    # build once at startup if missing, then on a fixed interval
    if not os.path.exists(BOARD):
        try:
            _rebuild()
        except Exception as e:
            print("startup build failed:", e)
    while True:
        time.sleep(REFRESH_HOURS * 3600)
        try:
            _rebuild()
        except Exception as e:
            print("scheduled build failed:", e)


@app.on_event("startup")
def _maybe_start_scheduler():
    if AUTO:
        threading.Thread(target=_scheduler, daemon=True).start()
        print(f"[scheduler] auto-refresh every {REFRESH_HOURS}h")
