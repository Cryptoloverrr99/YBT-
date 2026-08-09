# Deriv YBT LH Monitor — Final package

## What it does
- Deriv public market-data API, no trading/account authentication.
- Dynamically discovers active symbols.
- Filters Forex, commodities, indices and synthetic/derived markets.
- Scans instruments sequentially.
- Loads H1/H2/H3/H4 candles.
- Implements the computational YBT LH v2.2 logic supplied by the user: pivot detection, ATR merge clustering, volume boost, freshness weighting, lifecycle/fade/purge and magnet/readiness metrics.
- Sends one Telegram alert for each genuinely newly-created zone that meets the alert score threshold.
- Checks multi-timeframe alignment and assigns 1–4 stars.
- SQLite deduplication prevents the same zone from being sent repeatedly during normal operation.
- Lightweight Charts 5.2.0 is included in the dashboard shell.

## Important source-faithfulness note
The supplied Pine script's visual rendering is chart-only. The backend reproduces its computational logic; the web dashboard is a separate visualization layer. Multi-timeframe alignment and Telegram alert formatting are custom additions requested for this project.

## Local
1. Copy `.env.example` to `.env`.
2. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
3. `python -m venv .venv`
4. Activate the venv.
5. `pip install -r requirements.txt`
6. `pytest -q`
7. `python -m app.main`

## Render
This repository contains `Dockerfile` and `render.yaml`. Create a private GitHub repository, upload the project files, then create a Render Background Worker from the repository. Add the Telegram secrets as environment variables. The worker is the 24/7 scanner; the FastAPI dashboard is a separate service if you want a public UI.

### Persistence warning
The included SQLite path on the Render worker is `/tmp/alerts.sqlite3`, which is ephemeral. For strict no-duplicate behavior across server restarts, use a persistent disk or external Postgres/Redis and replace `AlertDeduplicator` storage. During normal uninterrupted operation, the SQLite store prevents duplicate alerts.
