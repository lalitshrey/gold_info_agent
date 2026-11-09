## Stock News Agent

Fetch stock news from multiple RSS sources (Google News, Yahoo Finance), deduplicate, and annotate with VADER sentiment. Provides both a CLI and a FastAPI endpoint.

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r AI_agent/stock_news_agent/requirements.txt
```

### CLI Usage

```bash
python AI_agent/stock_news_agent/app.py --tickers AAPL,TSLA --limit 20 --days 7
python AI_agent/stock_news_agent/app.py --tickers NVDA --json
```

### API Usage

Run the server:

```bash
uvicorn AI_agent.stock_news_agent.app:api --host 0.0.0.0 --port 8000
```

Open UI in browser:

```bash
xdg-open http://localhost:8000/
```

Query:

```bash
curl 'http://localhost:8000/news?tickers=AAPL,TSLA&limit=20&days=7'
```

### Notes

- First run will download NLTK's VADER lexicon automatically.
- Google News query uses `when:<days>d` for recent articles.
- Results include `sentiment.compound` in [-1, 1] (negative to positive).

### UI

- Root route `/` serves a simple Tailwind-based page to search tickers and view results.
- You can pass query params in the URL like `/?tickers=AAPL,TSLA&limit=20&days=7`.
- If running on a server, expose the port and open the URL from your machine.

