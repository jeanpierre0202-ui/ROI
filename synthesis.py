"""
synthesis.py — the "juice": triangulate signals of different directions into a
reasoned conclusion.

Two layers:
  1. consensus()  — DETERMINISTIC. Each source (quant, gov flows, global news,
     social) casts a directional vote. "Conviction" measures how much the
     evidence AGREES — it is NOT a probability of profit, and disagreement is
     shown openly. Runs for every name, free.
  2. dossier()    — AI synthesis (Anthropic + web search). Fuses all the above
     plus live worldwide reporting (analyst views, EU/Asia political &
     regulatory context, geopolitics) into a bull case, bear case, conclusion,
     multi-factor risk, and cited sources. Runs for the top names, costs API.
"""
from __future__ import annotations
import json
from typing import Dict, List

import requests

from . import config


# ----------------------------- consensus -----------------------------------
def _quant_direction(item: Dict, horizon: str) -> int:
    sig = item.get("signal_long" if horizon == "long" else "signal_short", 50)
    rsi = item.get("rsi", 50)
    m30 = item.get("changes", {}).get("d30", 0)
    if sig >= 60 and rsi < 72 and m30 > -3:
        return 1
    if sig <= 45 or rsi > 74 or m30 < -8:
        return -1
    return 0


def _flow_direction(flow_note: str) -> int:
    n = (flow_note or "").lower()
    if "buying" in n:
        return 1
    if "selling" in n:
        return -1
    return 0


def _news_direction(news: Dict) -> int:
    if not news or not news.get("available"):
        return 0
    t = news.get("tone", 0)
    return 1 if t > 1.0 else -1 if t < -1.0 else 0


_LABELS = {1: "Bullish", 0: "Neutral", -1: "Bearish"}
_WEIGHTS = {"Quant": 1.0, "Gov flows": 0.85, "Global news": 0.9, "Social": 0.55}


def consensus(item: Dict, horizon: str, flow_note: str, news: Dict, social: Dict) -> Dict:
    votes: Dict[str, int] = {"Quant": _quant_direction(item, horizon)}
    fd = _flow_direction(flow_note)
    if flow_note:
        votes["Gov flows"] = fd
    nd = _news_direction(news)
    if news and news.get("available"):
        votes["Global news"] = nd
    if social and social.get("available"):
        votes["Social"] = social.get("direction", 0)

    wtot = sum(_WEIGHTS[k] for k in votes)
    wsum = sum(_WEIGHTS[k] * v for k, v in votes.items())
    net = wsum / wtot if wtot else 0.0           # -1..1
    agreement = abs(net)                          # how aligned
    coverage = min(len(votes) / 4.0, 1.0)         # how many independent sources weighed in
    conviction = round(100 * agreement * (0.55 + 0.45 * coverage))

    direction = "Bullish" if net > 0.18 else "Bearish" if net < -0.18 else "Mixed"
    agree = [k for k, v in votes.items() if (v > 0 and net > 0) or (v < 0 and net < 0)]
    disagree = [k for k, v in votes.items() if v != 0 and ((v > 0) != (net > 0))]
    if direction == "Mixed":
        note = "Sources point in different directions — no clear edge."
    else:
        note = f"{len(agree)} of {len(votes)} signals lean {direction.lower()}"
        if disagree:
            note += f"; {', '.join(disagree)} disagree(s)"
        note += "."

    return {
        "direction": direction,
        "conviction": conviction,
        "votes": [{"source": k, "label": _LABELS[v]} for k, v in votes.items()],
        "note": note,
    }


# ----------------------------- AI dossier -----------------------------------
# Provider-flexible. Pick whichever free key is set; falls back to Anthropic.
# All providers are grounded on the free GDELT headlines we already fetched, so
# no paid web search is required.

def _call_gemini(prompt: str, max_tokens: int) -> str:
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.4}}
    r = requests.post(url, json=body, timeout=120)
    r.raise_for_status()
    data = r.json()
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def _call_openai_compatible(prompt: str, max_tokens: int, base: str, key: str, model: str) -> str:
    r = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "max_tokens": max_tokens, "temperature": 0.4,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _call_anthropic(prompt: str, max_tokens: int) -> str:
    headers = {"x-api-key": config.ANTHROPIC_API_KEY,
               "anthropic-version": "2023-06-01", "content-type": "application/json"}
    body = {"model": config.ANTHROPIC_MODEL, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    if config.SYNTHESIS_WEB_SEARCH:
        body["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}]
    r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=180)
    r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")


def _llm(prompt: str, max_tokens: int = 1400) -> str:
    p = config.active_provider()
    if p == "gemini":
        return _call_gemini(prompt, max_tokens)
    if p == "groq":
        return _call_openai_compatible(prompt, max_tokens, "https://api.groq.com/openai/v1",
                                       config.GROQ_API_KEY, config.GROQ_MODEL)
    if p == "openrouter":
        return _call_openai_compatible(prompt, max_tokens, "https://openrouter.ai/api/v1",
                                       config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
    if p == "anthropic":
        return _call_anthropic(prompt, max_tokens)
    raise RuntimeError("no synthesis provider configured")


def _parse_json(text: str):
    if not text:
        return None
    t = text.replace("```json", "").replace("```", "").strip()
    a, b = t.find("{"), t.rfind("}")
    if a == -1 or b == -1:
        return None
    try:
        return json.loads(t[a:b + 1])
    except Exception:
        return None


def dossier(name: str, ticker: str, asset_kind: str, item: Dict,
            cons: Dict, flow_note: str, news: Dict, social: Dict) -> Dict | None:
    if config.active_provider() == "none":
        return None
    headlines = [f"- {h.get('title','')} ({h.get('country','')}, {h.get('domain','')})"
                 for h in (news.get("headlines") or [])][:6]
    ctx = {
        "quant_signal": item.get("signal"), "rsi": item.get("rsi"),
        "changes": item.get("changes"), "volatility": item.get("volatility"),
        "gov_flow": flow_note or "none",
        "news_tone": news.get("tone") if news else None,
        "news_volume": news.get("volume") if news else None,
        "news_countries": news.get("countries") if news else [],
        "social": {"direction": social.get("direction"), "mentions": social.get("mentions")} if social and social.get("available") else "none",
        "consensus": {"direction": cons.get("direction"), "conviction": cons.get("conviction"), "note": cons.get("note")},
    }
    hl_block = ("\nRecent global news headlines (real, from GDELT, last ~7 days):\n" + "\n".join(headlines)) if headlines else ""
    prompt = f"""You are ROI, an investment-intelligence analyst. Triangulate evidence from MULTIPLE directions into one reasoned conclusion for {name} ({ticker}), a {asset_kind}.

ROI's computed signals (use and weigh them critically):
{json.dumps(ctx, default=str)}{hl_block}

Weigh bullish AND bearish evidence honestly, including any geopolitical, regulatory, environmental or social factors implied by the headlines. Do NOT promise returns or certainty. The conclusion must reflect where the weight of evidence points and how much the sources agree or conflict.

Return ONLY minified JSON, nothing else, no markdown fences:
{{"bull":["<=16 words, evidence-based","..."],"bear":["<=16 words","..."],"conclusion":"<=45 words, balanced, references convergence/divergence of signals","risk":{{"economic":"<=14 words","geopolitical":"<=14 words","environmental_social":"<=14 words"}},"sources":[{{"title":"short","url":"https://..."}}]}}
2-4 bull, 2-4 bear. For sources, reuse the headline domains/links above. Paraphrase; no long quotes."""
    try:
        return _parse_json(_llm(prompt))
    except Exception:
        return None
