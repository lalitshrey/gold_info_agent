# Stock News Agent

An async Python agent that aggregates recent news for stock tickers from multiple sources (RSS feeds and Yahoo Finance RSS). Provides a simple CLI to query tickers and print unified results.

## Features
- Async fetching with connection pooling
- Pluggable providers (RSS, Yahoo Finance RSS)
- Unified typed model with source metadata and deduplication
- CLI with nice output using Rich

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Example: fetch AAPL and MSFT news
python -m stock_news_agent.cli AAPL MSFT --limit 20 --minutes 720
```

## Usage

```bash
python -m stock_news_agent.cli [TICKERS ...] [OPTIONS]
```

Options:
- `--minutes` lookback window in minutes (default 1440 = 24h)
- `--limit` maximum items to display after merge+dedupe (default 50)
- `--format` output format: `rich` (default) or `json`

## Configuration

RSS sources are defined in `stock_news_agent/providers/rss_provider.py`. You can customize or add feeds. Yahoo Finance provider uses Yahoo's public RSS endpoint per ticker.

## Notes
- This agent uses public RSS feeds; respect each source's terms.
- Network errors are handled gracefully; failures of a source won't break the whole run.

## Development
- Python 3.10+
- Run `ruff` and `mypy` if you add them; not required for basic usage.
# gold_info_agent
