# ROI — Investing Intelligence

*Le roi de votre portefeuille.* The brain of a portfolio, not a fund — it never takes your money or places trades. It computes a ranked, sourced, risk-aware view from **real data** and shows its work.

The engine pulls genuine sources, computes transparent quant scores, and writes `board.json`. The frontend only renders that file — so your API keys stay on the server and the browser never invents anything.

```
                 ┌─────────────────────────────────────────────┐
   real sources  │  Stooq prices · SEC EDGAR · FRED · congress  │
                 │  disclosures · CoinGecko                      │
                 └───────────────────┬─────────────────────────┘
                                     ▼
                        engine/build_board.py
              (RSI, volatility, momentum, depth, scoring,
               crown-tier, buy/hold/sell triggers, sources)
                                     ▼
                              data/board.json
                                     ▼
                     web/  (static React, renders board.json)
```

## What's real

- **Equities** — daily closes & volume from **Stooq** (no key). RSI(14), annualised volatility, 1d/7d/30d momentum, 30-day pivot & support, and a real dollar-volume depth percentile are all **computed**, not asserted.
- **Catalysts** — **SEC EDGAR** recent 8-K / Form 4 (insider) / 10-Q filings, with links.
- **Flows** — congressional (STOCK Act) disclosures via public community mirrors. *These mirrors can go stale; see the honesty note in `engine/sources/congress.py`. Swap in a maintained API for production.*
- **Macro** — **FRED** (St. Louis Fed): rates, the 10y–2y curve, CPI, unemployment, VIX, USD, oil → a plain-English regime read.
- **Crypto** — **CoinGecko** live market data.

`signal` (0–100) is a transparent weighted blend of the component bars shown on each card. It ranks relative attractiveness — **not** a probability of profit. Markets carry real risk of loss. This is research, not financial advice.

## Run it locally

```bash
git clone <your-repo> roi && cd roi
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add a free FRED key + your SEC user-agent email

python -m engine.build_board   # writes data/board.json and web/public/board.json

cd web && npm install && npm run dev   # open the URL it prints
```

Only **two** things to obtain, both free:
- **FRED_API_KEY** — https://fredaccount.stlouisfed.org/apikeys (lights up the macro strip)
- **SEC_USER_AGENT** — just set it to `ROI Research your-name your-email@example.com` (SEC requires a real contact)

Everything else (Stooq, CoinGecko, congressional mirrors) needs no key. The engine **degrades gracefully** — if a source is down or a key is missing, it skips that piece instead of crashing or faking it.

---

## Hosting for daily updates

You want the board to refresh every morning on its own. Three solid paths, cheapest first. *(Provider features and prices change — confirm current limits before committing.)*

### 1. GitHub Actions + a static host  — **free, recommended**

The included workflow `.github/workflows/daily.yml` runs every weekday, rebuilds `board.json`, and commits it. A static host serves the file. No server to keep alive.

1. Push this repo to GitHub (a **public** repo gets unlimited free Action minutes).
2. Repo → Settings → Secrets and variables → Actions → add `FRED_API_KEY` and `SEC_USER_AGENT`.
3. Actions tab → run **ROI daily board** once manually (this also "arms" the schedule).
4. Host `web/` for free on **Netlify**, **Vercel**, **Cloudflare Pages**, **GitHub Pages**, or a Render static site — build `npm run build`, publish `web/dist`. The committed `web/public/board.json` ships with each build.

Worth knowing about Action cron (so nothing surprises you):
- Schedules run in **UTC** and can be **delayed 10–30 min** under load — fine for a daily board, not for second-precise jobs.
- In a public repo, scheduled workflows **auto-disable after 60 days of no repo activity** — but the daily commit *is* activity, so it self-sustains. If you ever pause it, just re-enable from the Actions tab.
- The frontend reads the file the static host already serves; for the freshest data, set your host to rebuild on each push to `main` (Netlify/Vercel do this by default).

### 2. Render — **one self-contained service** (~$7/mo, or free-with-sleep)

Render cron jobs **can't share a disk** with a web service, so instead the included `api/main.py` rebuilds on its own background schedule. `render.yaml` deploys a single web service with `ROI_AUTO_REFRESH=1` (rebuilds every 24h, serves `/api/board`).

1. New → Blueprint → point at this repo (`render.yaml`).
2. Add `FRED_API_KEY` and `SEC_USER_AGENT` in the service's Environment.
3. Deploy. Host `web/` as a free Render **static site** and point it at `/api/board`, or keep using the GitHub Actions file.

The Starter instance (~$7/mo) stays always-on. The free instance works but **sleeps after inactivity**, so the first request after idle is slow.

### 3. Other options

- **Railway** — free plan is a 30-day trial with $5 credit, then ~$1/mo limited or $5/mo Hobby. Run `api/main.py` with `ROI_AUTO_REFRESH=1`, same as Render.
- **Fly.io** — supports scheduled machines; good if you want regions/control.
- **PythonAnywhere** — has built-in **daily scheduled tasks** (verify current free-tier task limits); point a daily task at `python -m engine.build_board`.
- **A $5 VPS** (Hetzner/DigitalOcean) + system `cron` — cheapest always-on; run the build from crontab and serve `web/dist` with any static server.

**Recommendation:** start with **#1 (GitHub Actions + Netlify/Vercel)**. It's free, needs no server, and the schedule lives next to your code. Move to **#2** only when you want a live API with on-demand `/api/refresh`.

---

## Extending

- **More reliable congressional data** — reimplement `engine.sources.congress.recent_trades()` against a maintained API (Quiver Quantitative, Capitol Trades, Unusual Whales).
- **Wider universe** — set `ROI_UNIVERSE` or edit `engine/config.py`. With Stooq, ~40 names build comfortably; larger sets just take longer (the build sleeps 0.4s between tickers to stay polite).
- **AI narratives** — set `ANTHROPIC_API_KEY` and add a `narrative.py` step if you want model-written theses with citations on top of the quant base. The current theses are rule-based and need no LLM.

## Disclaimer

ROI is an information and research tool — not a broker, adviser, or fiduciary, and nothing here is a recommendation to buy or sell any security or asset. Markets carry real risk of loss. Verify with primary sources and a licensed professional before acting.
