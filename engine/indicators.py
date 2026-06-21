"""
indicators.py — transparent quantitative math.

Everything here is computed from real price series. No magic, no fabrication.
Each function is small and auditable so the "why" behind a score is traceable.
"""
from __future__ import annotations
from statistics import mean, pstdev
from typing import List, Dict


def pct_returns(prices: List[float]) -> List[float]:
    out = []
    for i in range(1, len(prices)):
        if prices[i - 1]:
            out.append((prices[i] - prices[i - 1]) / prices[i - 1])
    return out


def rsi(prices: List[float], period: int = 14) -> float:
    """Wilder-style RSI on a close series."""
    if len(prices) < period + 1:
        return 50.0
    gain = loss = 0.0
    for i in range(len(prices) - period, len(prices)):
        d = prices[i] - prices[i - 1]
        if d >= 0:
            gain += d
        else:
            loss -= d
    if loss == 0:
        return 100.0
    rs = gain / loss
    return 100.0 - 100.0 / (1.0 + rs)


def volatility(prices: List[float]) -> float:
    """Annualised-ish daily volatility in %, from daily returns."""
    r = pct_returns(prices)
    if len(r) < 2:
        return 0.0
    return pstdev(r) * (252 ** 0.5) * 100.0


def momentum(prices: List[float], lookback: int) -> float:
    """% change over `lookback` sessions."""
    if len(prices) <= lookback or not prices[-lookback - 1]:
        return 0.0
    return (prices[-1] - prices[-lookback - 1]) / prices[-lookback - 1] * 100.0


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def score_series(prices: List[float], depth_pctile: float) -> Dict:
    """
    Build the two composite scores used everywhere in ROI, plus the levels
    and stance. `depth_pctile` (0-100) encodes liquidity/market depth — for
    equities use dollar-volume rank, for crypto use market-cap rank.

    SIGNAL  = opportunity (trend + momentum, volatility-aware)
    SECURITY = resilience (depth + low volatility + sane RSI)
    """
    px = prices[-1]
    window = prices[-30:] if len(prices) >= 30 else prices
    pivot = mean(window) if window else px
    support = min(window) if window else px

    r = rsi(prices, 14)
    vol = volatility(prices)
    m1 = momentum(prices, 1)
    m7 = momentum(prices, 5)     # ~1 trading week
    m30 = momentum(prices, 21)   # ~1 trading month
    above_mean = px >= pivot

    # sub-scores, all 0..100
    s_mom = clamp(50 + m1 * 4, 0, 100)
    s_trend = clamp(50 + m7 * 1.6, 0, 100)
    s_long_trend = clamp(50 + m30 * 0.8, 0, 100)
    vol_score = clamp(100 - vol * 0.9, 0, 100)          # lower vol -> higher
    rsi_balance = clamp(100 - abs(r - 55) * 2.2, 0, 100)  # healthy momentum band
    depth = clamp(depth_pctile, 0, 100)

    signal_short = round(0.34 * s_mom + 0.30 * s_trend + 0.20 * rsi_balance + 0.16 * vol_score)
    signal_long = round(0.40 * s_long_trend + 0.24 * depth + 0.22 * vol_score + 0.14 * rsi_balance)
    security = round(0.42 * depth + 0.34 * vol_score + 0.24 * rsi_balance)

    if r >= 72:
        action, tone = "Trim / take profit", "warn"
    elif r <= 34 and m30 > -25:
        action, tone = "Accumulate zone", "buy"
    elif above_mean and m7 > 0:
        action, tone = "Hold — trend intact", "hold"
    elif (not above_mean) and m7 < 0:
        action, tone = "Caution — below pivot", "warn"
    else:
        action, tone = "Neutral — wait", "neutral"

    return {
        "price": round(px, 6),
        "rsi": round(r, 1),
        "volatility": round(vol, 2),
        "changes": {"d1": round(m1, 2), "d7": round(m7, 2), "d30": round(m30, 2)},
        "levels": {"pivot": round(pivot, 6), "support": round(support, 6)},
        "components": {
            "momentum": round(s_mom),
            "trend7d": round(s_trend),
            "trend30d": round(s_long_trend),
            "low_volatility": round(vol_score),
            "rsi_balance": round(rsi_balance),
            "market_depth": round(depth),
        },
        "signal_short": signal_short,
        "signal_long": signal_long,
        "security": security,
        "action": action,
        "action_tone": tone,
        "above_mean": above_mean,
    }
