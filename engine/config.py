"""
config.py — what ROI watches, and how it reads its keys.

The equity universe is intentionally a curated, liquid set across sectors.
Override it with ROI_UNIVERSE (comma-separated tickers) in the environment.
"""
from __future__ import annotations
import os

# ---- API keys (all optional; the engine degrades gracefully without them) ----
FRED_API_KEY = os.getenv("FRED_API_KEY", "").strip()
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
# SEC requires a descriptive UA with a contact. Set yours.
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "ROI Research roi-research@example.com").strip()

PRICE_PROVIDER = os.getenv("ROI_PRICE_PROVIDER", "stooq").strip().lower()  # stooq | alphavantage

# ---- equity universe -------------------------------------------------------
_DEFAULT_UNIVERSE = {
    # Mega-cap tech / comms
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Semiconductors",
    "GOOGL": "Communication Svcs", "META": "Communication Svcs", "AMZN": "Consumer Discretionary",
    "AVGO": "Semiconductors", "AMD": "Semiconductors", "ORCL": "Technology", "CRM": "Technology",
    "ADBE": "Technology", "NFLX": "Communication Svcs",
    # Financials
    "JPM": "Financials", "BAC": "Financials", "GS": "Financials", "V": "Financials",
    "MA": "Financials", "BRK-B": "Financials",
    # Healthcare
    "UNH": "Healthcare", "LLY": "Healthcare", "JNJ": "Healthcare", "ABBV": "Healthcare",
    "MRK": "Healthcare",
    # Industrials / energy / materials
    "CAT": "Industrials", "BA": "Industrials", "GE": "Industrials",
    "XOM": "Energy", "CVX": "Energy",
    # Consumer staples / discretionary
    "COST": "Consumer Staples", "WMT": "Consumer Staples", "PG": "Consumer Staples",
    "HD": "Consumer Discretionary", "MCD": "Consumer Discretionary", "TSLA": "Consumer Discretionary",
    # Utilities / real estate
    "NEE": "Utilities", "PLD": "Real Estate",
}


def universe() -> dict:
    raw = os.getenv("ROI_UNIVERSE", "").strip()
    if not raw:
        return dict(_DEFAULT_UNIVERSE)
    out = {}
    for t in raw.split(","):
        t = t.strip().upper()
        if t:
            out[t] = _DEFAULT_UNIVERSE.get(t, "Other")
    return out


# ---- crypto sectors --------------------------------------------------------
CRYPTO_SECTOR = {
    "bitcoin": "Store of Value", "ethereum": "Smart Contract L1", "solana": "Smart Contract L1",
    "cardano": "Smart Contract L1", "avalanche-2": "Smart Contract L1", "binancecoin": "Exchange / L1",
    "ripple": "Payments", "polkadot": "Interoperability", "chainlink": "Oracles / DeFi",
    "uniswap": "DeFi", "aave": "DeFi", "matic-network": "Scaling / L2", "polygon": "Scaling / L2",
    "arbitrum": "Scaling / L2", "optimism": "Scaling / L2", "dogecoin": "Meme / Culture",
    "shiba-inu": "Meme / Culture", "pepe": "Meme / Culture", "litecoin": "Payments",
    "bitcoin-cash": "Payments", "cosmos": "Interoperability", "near": "Smart Contract L1",
    "aptos": "Smart Contract L1", "sui": "Smart Contract L1", "tron": "Smart Contract L1",
    "stellar": "Payments", "internet-computer": "Compute", "filecoin": "Storage",
    "render-token": "Compute / AI", "the-graph": "Data / Infra", "injective": "DeFi",
    "hedera-hashgraph": "Enterprise L1", "monero": "Privacy",
}
STABLES = {
    "tether", "usd-coin", "dai", "first-digital-usd", "true-usd", "usdd", "frax",
    "paypal-usd", "binance-usd", "ethena-usde", "usds",
}


def crypto_sector(coin_id: str) -> str:
    return CRYPTO_SECTOR.get(coin_id, "Other")
