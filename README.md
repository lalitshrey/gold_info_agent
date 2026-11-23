# Market Data Tools

This repository contains a precious-metals browser dashboard and separate
stock-news and bond-yield tools. See [architecture.md](architecture.md) for
how the applications fit together.

## Precious-metals dashboard

Install the root requirements, set login credentials and a persistent session
secret, then start the web app:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export PRECIOUS_DASHBOARD_USERNAME=admin
export PRECIOUS_DASHBOARD_PASSWORD='choose-a-long-password'
export PRECIOUS_DASHBOARD_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
python precious_metals_dashboard.py
```

Open <http://127.0.0.1:8002/>. The dashboard has Overview, Gold, Silver, and
Sources sections, an on-demand refresh button, and signed-cookie login/logout.
Set `PRECIOUS_DASHBOARD_COOKIE_SECURE=1` when serving over HTTPS. Keep the
username, password, and session secret private; configure them in the process
environment rather than committing them to the repository.

The page fetches COMEX, USD/INR, and Indian market quotes on initial load and
refresh. It can show partial results when an individual provider is unavailable.
COMEX conversions are indicative benchmarks and are displayed separately from
the specific Indian market quotes.

## Stock-news and bond-yield tools

The separate applications under `stock_news_agent/` include a FastAPI stock
news app, an asynchronous RSS CLI, and a U.S. bond-yield browser dashboard.
Their setup and commands are documented in
[`stock_news_agent/README.md`](stock_news_agent/README.md).
