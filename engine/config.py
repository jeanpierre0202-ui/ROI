"""
config.py — what ROI watches, and how it reads its keys.
"""
from __future__ import annotations
import os

# ---- API keys -------------------------------------------------------------
FRED_API_KEY = os.getenv("FRED_API_KEY", "").strip()
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "").strip()
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "ROI Research roi-research@example.com").strip()
PRICE_PROVIDER = os.getenv("ROI_PRICE_PROVIDER", "stooq").strip().lower()

# ---- synthesis layer (the "juice") ----------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

SYNTHESIS_PROVIDER = os.getenv("ROI_SYNTHESIS_PROVIDER", "auto").strip().lower()
GEMINI_MODEL = os.getenv("ROI_GEMINI_MODEL", "gemini-2.0-flash").strip()
GROQ_MODEL = os.getenv("ROI_GROQ_MODEL", "llama-3.3-70b-versatile").strip()
OPENROUTER_MODEL = os.getenv("ROI_OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free").strip()
ANTHROPIC_MODEL = os.getenv("ROI_SYNTHESIS_MODEL", "claude-sonnet-4-6").strip()
SYNTHESIS_WEB_SEARCH = os.getenv("ROI_SYNTHESIS_WEB_SEARCH", "0").strip() not in ("0", "false", "no", "")

try:
    SYNTHESIS_MAX_NAMES = int(os.getenv("ROI_SYNTHESIS_MAX_NAMES", "12"))
except ValueError:
    SYNTHESIS_MAX_NAMES = 12


def active_provider() -> str:
    """Which LLM will write dossiers, based on override + available keys."""
    if SYNTHESIS_PROVIDER != "auto":
        return SYNTHESIS_PROVIDER
    if GEMINI_API_KEY:
        return "gemini"
    if GROQ_API_KEY:
        return "groq"
    if OPENROUTER_API_KEY:
        return "openrouter"
    if ANTHROPIC_API_KEY:
        return "anthropic"
    return "none"


MARKETAUX_API_KEY = os.getenv("MARKETAUX_API_KEY", "").strip()
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "").strip()
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "roi-research/1.0").strip()

# ---- equity universe + company names --------------------------------------
_UNIVERSE = {
    "AAPL": ("Apple", "Technology"), "MSFT": ("Microsoft", "Technology"),
    "NVDA": ("Nvidia", "Semiconductors"), "GOOGL": ("Alphabet", "Communication Svcs"),
    "META": ("Meta Platforms", "Communication Svcs"), "AMZN": ("Amazon", "Consumer Discretionary"),
    "AVGO": ("Broadcom", "Semiconductors"), "AMD": ("AMD", "Semiconductors"),
    "ORCL": ("Oracle", "Technology"), "CRM": ("Salesforce", "Technology"),
    "ADBE": ("Adobe", "Technology"), "NFLX": ("Netflix", "Communication Svcs"),
    "JPM": ("JPMorgan Chase", "Financials"), "BAC": ("Bank of America", "Financials"),
    "GS": ("Goldman Sachs", "Financials"), "V": ("Visa", "Financials"),
    "MA": ("Mastercard", "Financials"), "BRK-B": ("Berkshire Hathaway", "Financials"),
    "UNH": ("UnitedHealth", "Healthcare"), "LLY": ("Eli Lilly", "Healthcare"),
    "JNJ": ("Johnson & Johnson", "Healthcare"), "ABBV": ("AbbVie", "Healthcare"),
    "MRK": ("Merck", "Healthcare"), "CAT": ("Caterpillar", "Industrials"),
    "BA": ("Boeing", "Industrials"), "GE": ("GE Aerospace", "Industrials"),
    "XOM": ("Exxon Mobil", "Energy"), "CVX": ("Chevron", "Energy"),
    "COST": ("Costco", "Consumer Staples"), "WMT": ("Walmart", "Consumer Staples"),
    "PG": ("Procter & Gamble", "Consumer Staples"), "HD": ("Home Depot", "Consumer Discretionary"),
    "MCD": ("McDonald's", "Consumer Discretionary"), "TSLA": ("Tesla", "Consumer Discretionary"),
    "NEE": ("NextEra Energy", "Utilities"), "PLD": ("Prologis", "Real Estate"),
}


def universe() -> dict:
    raw = os.getenv("ROI_UNIVERSE", "").strip()
    if not raw:
        return {t: s for t, (_n, s) in _UNIVERSE.items()}
    out = {}
    for t in raw.split(","):
        t = t.strip().upper()
        if t:
            out[t] = _UNIVERSE.get(t, ("", "Other"))[1]
    return out


def company_name(ticker: str) -> str:
    return _UNIVERSE.get(ticker.upper(), (ticker, ""))[0] or ticker


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
