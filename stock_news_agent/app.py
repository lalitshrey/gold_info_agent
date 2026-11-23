import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
from pathlib import Path
from typing import Dict, List, Optional, Set

import feedparser
import re
import html as html_lib
import logging
from urllib.parse import quote_plus
import httpx
import trafilatura
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk import download as nltk_download, data as nltk_data
from zoneinfo import ZoneInfo

# Import database modules
from database import init_database
from stock_service import (
    get_nifty_stocks, get_nifty_symbols, get_stocks_by_sector,
    search_nifty_stocks, validate_nifty_symbols, get_nifty_sectors,
    get_nifty_stats, stock_service
)

_logger = logging.getLogger(__name__)


# ---------- Utilities ----------
def _ensure_vader_downloaded() -> None:
    """Ensure the NLTK VADER lexicon is available at runtime."""
    try:
        nltk_data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        nltk_download("vader_lexicon")


def _isoformat(published: Optional[dt.datetime]) -> Optional[str]:
    if not published:
        return None
    if published.tzinfo is None:
        # Assume UTC when timezone is missing
        published = published.replace(tzinfo=dt.timezone.utc)
    return published.isoformat()


_TAGS_RE = re.compile(r"<[^>]+>")


def _strip_html(value: Optional[str]) -> str:
    if not value:
        return ""
    # Unescape HTML entities first, then remove tags
    unescaped = html_lib.unescape(str(value))
    return _TAGS_RE.sub("", unescaped).strip()


def _first_n_words(text: str, n: int = 50) -> str:
    words = text.split()
    if len(words) <= n:
        return " ".join(words)
    return " ".join(words[:n])


def _extract_preview_from_link(link: Optional[str], n_words: int = 50) -> str:
    if not link:
        return ""
    try:
        headers = {"User-Agent": "stock-news-agent/1.0"}
        with httpx.Client(headers=headers, timeout=10) as client:
            resp = client.get(link, follow_redirects=True)
            resp.raise_for_status()
            text = trafilatura.extract(resp.text) or ""
            text_clean = _strip_html(text)
            return _first_n_words(text_clean, n_words)
    except Exception:
        return ""


def _parse_struct_time(value) -> Optional[dt.datetime]:
    if value is None:
        return None
    try:
        return dt.datetime.fromtimestamp(
            dt.datetime(*value[:6]).timestamp(), tz=dt.timezone.utc
        )
    except Exception:
        return None


def _now_utc() -> dt.datetime:
    return dt.datetime.now(tz=dt.timezone.utc)


def _format_india_time(value: Optional[dt.datetime]) -> Optional[str]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    ist = ZoneInfo("Asia/Kolkata")
    local = value.astimezone(ist)
    return local.strftime("%Y-%m-%d %H:%M:%S")


# ---------- News Sources ----------
def fetch_google_news(
    ticker: str,
    days: int = 7,
    limit: int = 25,
) -> List[Dict]:
    """Fetch news from Google News RSS for a ticker symbol."""
    query = f"{ticker} when:{days}d"
    query_enc = quote_plus(query)
    url = (
        "https://news.google.com/rss/search?"
        f"q={query_enc}&hl=en-US&gl=US&ceid=US:en"
    )
    feed = feedparser.parse(url)
    articles: List[Dict] = []
    for entry in feed.entries[:limit]:
        published_parsed = getattr(entry, "published_parsed", None)
        published_dt = _parse_struct_time(published_parsed) or _now_utc()
        articles.append(
            {
                "title": _strip_html(getattr(entry, "title", "")),
                "summary": _strip_html(getattr(entry, "summary", "")),
                "link": getattr(entry, "link", ""),
                "published": published_dt,
                "source": "Google News",
                "ticker": ticker.upper(),
            }
        )
    return articles


def fetch_yahoo_finance(ticker: str, limit: int = 25) -> List[Dict]:
    """Fetch news from Yahoo Finance RSS for a ticker symbol."""
    url = (
        "https://feeds.finance.yahoo.com/rss/2.0/headline?"
        f"s={ticker}&region=US&lang=en-US"
    )
    feed = feedparser.parse(url)
    articles: List[Dict] = []
    for entry in feed.entries[:limit]:
        published_parsed = getattr(entry, "published_parsed", None)
        published_dt = _parse_struct_time(published_parsed) or _now_utc()
        articles.append(
            {
                "title": _strip_html(getattr(entry, "title", "")),
                "summary": _strip_html(getattr(entry, "summary", "")),
                "link": getattr(entry, "link", ""),
                "published": published_dt,
                "source": "Yahoo Finance",
                "ticker": ticker.upper(),
            }
        )
    return articles


# ---------- Aggregation and Sentiment ----------
def _deduplicate(articles: List[Dict]) -> List[Dict]:
    seen: Set[str] = set()
    unique: List[Dict] = []
    for a in articles:
        key = (a.get("link") or a.get("title") or "").strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        unique.append(a)
    return unique


def _add_sentiment(articles: List[Dict]) -> List[Dict]:
    _ensure_vader_downloaded()
    sia = SentimentIntensityAnalyzer()
    for a in articles:
        text = f"{a.get('title', '')}\n{a.get('summary', '')}".strip()
        if text:
            score = sia.polarity_scores(text)
            a["sentiment"] = {
                "compound": score.get("compound", 0.0),
                "pos": score.get("pos", 0.0),
                "neu": score.get("neu", 0.0),
                "neg": score.get("neg", 0.0),
            }
        else:
            a["sentiment"] = {
                "compound": 0.0,
                "pos": 0.0,
                "neu": 1.0,
                "neg": 0.0,
            }
        # Convert datetime to ISO string and India time string
        a["published_iso"] = _isoformat(a.get("published"))
        a["published_india"] = _format_india_time(a.get("published"))
        # First 50 words preview: prefer summary; fallback to fetching article
        summary_text = (a.get("summary") or "").strip()
        summary_first50 = _first_n_words(summary_text, 50)
        if summary_first50:
            a["preview_first50"] = summary_first50
        else:
            a["preview_first50"] = _extract_preview_from_link(
                a.get("link"),
                50,
            )
    return articles


def get_news(
    tickers: List[str],
    per_source_limit: int = 20,
    google_days: int = 7,
) -> List[Dict]:
    """Aggregate, deduplicate, sentiment-score and sort news for tickers."""
    collected: List[Dict] = []
    for t in tickers:
        t_clean = t.strip()
        if not t_clean:
            continue
        collected.extend(
            fetch_google_news(
                t_clean,
                days=google_days,
                limit=per_source_limit,
            )
        )
        collected.extend(fetch_yahoo_finance(t_clean, limit=per_source_limit))

    if not collected:
        return []

    collected = _deduplicate(collected)
    collected = _add_sentiment(collected)
    collected.sort(
        key=lambda x: x.get("published") or _now_utc(),
        reverse=True,
    )
    # Remove raw datetime before returning to avoid non-serializable objects
    for a in collected:
        a.pop("published", None)
    return collected


def _fetch_yahoo_price_change(symbol: str, since: dt.date) -> Dict:
    """Compare the latest Yahoo quote with the latest close on/before `since`."""
    yahoo_symbol = f"{symbol}.NS"
    start = dt.datetime.combine(
        since - dt.timedelta(days=10), dt.time.min, tzinfo=dt.timezone.utc
    )
    end = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote_plus(yahoo_symbol)}"
    response = httpx.get(
        url,
        params={
            "period1": int(start.timestamp()),
            "period2": int(end.timestamp()),
            "interval": "1d",
        },
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    response.raise_for_status()
    chart = response.json().get("chart", {})
    if chart.get("error"):
        raise ValueError(
            str(chart["error"].get("description") or "Yahoo Finance quote unavailable")
        )
    results = chart.get("result") or []
    if not results:
        raise ValueError("Yahoo Finance returned no price history")

    result = results[0]
    timestamps = result.get("timestamp") or []
    quote_data = (result.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote_data.get("close") or []
    history = [
        (dt.datetime.fromtimestamp(stamp, tz=dt.timezone.utc).date(), float(close))
        for stamp, close in zip(timestamps, closes)
        if close is not None
    ]
    base_points = [point for point in history if point[0] <= since]
    if not base_points:
        raise ValueError(f"No closing price available on or before {since.isoformat()}")

    baseline_date, baseline_close = base_points[-1]
    meta = result.get("meta", {})
    latest_price = meta.get("regularMarketPrice")
    if latest_price is None and history:
        latest_price = history[-1][1]
    if latest_price is None:
        raise ValueError("Yahoo Finance returned no latest price")

    latest_price = float(latest_price)
    change = latest_price - baseline_close
    return {
        "symbol": symbol,
        "yahoo_symbol": yahoo_symbol,
        "currency": meta.get("currency") or "INR",
        "baseline_date": baseline_date.isoformat(),
        "baseline_close": baseline_close,
        "latest_price": latest_price,
        "change": change,
        "change_pct": change / baseline_close * 100 if baseline_close else None,
        "market_time": meta.get("regularMarketTime"),
    }


def _safe_yahoo_price_change(symbol: str, since: dt.date) -> Dict:
    try:
        return _fetch_yahoo_price_change(symbol, since)
    except Exception as error:
        _logger.warning("Could not fetch Yahoo Finance quote for %s: %s", symbol, error)
        return {"symbol": symbol, "error": str(error)}


def get_stock_price_changes(symbols: List[str], since: dt.date) -> List[Dict]:
    """Fetch price movements for selected NSE symbols, tolerating source errors."""
    if not symbols:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(symbols))) as executor:
        return list(
            executor.map(
                lambda symbol: _safe_yahoo_price_change(symbol, since), symbols
            )
        )


# ---------- FastAPI ----------
api = FastAPI(title="Stock News Agent", version="0.1.0")

# Initialize database on startup


@api.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        if init_database():
            print("✅ Database initialized successfully")
        else:
            print("❌ Database initialization failed")
    except Exception as e:
        print(f"❌ Database startup error: {e}")

# Templates and static setup
_BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(_BASE_DIR / "templates"))
static_dir = _BASE_DIR / "static"
if static_dir.exists():
    api.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@api.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    tickers: Optional[str] = Query(
        None,
        description="Comma-separated tickers",
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
        description="Max items per source",
    ),
    days: int = Query(
        7,
        ge=1,
        le=30,
        description="Days back for Google News",
    ),
    since: Optional[dt.date] = Query(
        None,
        description="Compare the latest quote with the last close on or before this date",
    ),
):
    symbols: List[str] = []
    invalid_symbols: List[str] = []
    articles: List[Dict] = []
    prices: List[Dict] = []
    today = dt.datetime.now(ZoneInfo("Asia/Kolkata")).date()
    price_since = since or (today - dt.timedelta(days=1))
    price_error = ""
    if price_since > today:
        price_error = "Choose today or an earlier date for price comparison."
    if tickers:
        requested_symbols = list(
            dict.fromkeys(t.strip().upper() for t in tickers.split(",") if t.strip())
        )
        if requested_symbols:
            symbols, invalid_symbols = validate_nifty_symbols(requested_symbols)
        if symbols:
            articles = get_news(
                symbols,
                per_source_limit=limit,
                google_days=days,
            )
            if not price_error:
                prices = get_stock_price_changes(symbols, price_since)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "tickers": tickers or "",
            "limit": limit,
            "days": days,
            "symbols": symbols,
            "invalid_symbols": invalid_symbols,
            "articles": articles,
            "prices": prices,
            "price_since": price_since.isoformat(),
            "price_error": price_error,
            "max_date": today.isoformat(),
        },
    )


@api.get("/news")
def news_endpoint(
    tickers: str = Query(
        ..., description="Comma-separated ticker symbols"
    ),
    limit: int = Query(
        20, ge=1, le=100, description="Max items per source"
    ),
    days: int = Query(
        7, ge=1, le=30, description="How many days back for Google News"
    ),
):
    symbols = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not symbols:
        raise HTTPException(status_code=400, detail="No tickers provided")

    # Validate symbols against database
    valid_symbols, invalid_symbols = validate_nifty_symbols(symbols)
    if invalid_symbols:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ticker symbols: {', '.join(invalid_symbols)}"
        )

    articles = get_news(valid_symbols, per_source_limit=limit, google_days=days)
    return {"tickers": valid_symbols, "count": len(articles), "articles": articles}


# ---------- Database Endpoints ----------

@api.get("/stocks")
def get_stocks(
    limit: Optional[int] = Query(
        None, ge=1, le=1000, description="Limit number of stocks"
    ),
    sector: Optional[str] = Query(None, description="Filter by sector")
):
    """Get Nifty stocks from database."""
    try:
        if sector:
            stocks = get_stocks_by_sector(sector, limit)
        else:
            stocks = get_nifty_stocks(limit)
        return {"count": len(stocks), "stocks": stocks}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching stocks: {str(e)}"
        )


@api.get("/stocks/symbols")
def get_stock_symbols(
    limit: Optional[int] = Query(
        None, ge=1, le=1000, description="Limit number of symbols"
    )
):
    """Get list of Nifty stock symbols."""
    try:
        symbols = get_nifty_symbols(limit)
        return {"count": len(symbols), "symbols": symbols}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching symbols: {str(e)}"
        )


@api.get("/stocks/search")
def search_stocks(
    query: str = Query(
        ..., description="Search query for stock name or symbol"
    ),
    limit: Optional[int] = Query(
        None, ge=1, le=100, description="Limit number of results"
    )
):
    """Search stocks by name or symbol."""
    try:
        stocks = search_nifty_stocks(query, limit)
        return {"query": query, "count": len(stocks), "stocks": stocks}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error searching stocks: {str(e)}"
        )


@api.get("/stocks/sectors")
def get_sectors():
    """Get available sectors."""
    try:
        sectors = get_nifty_sectors()
        return {"count": len(sectors), "sectors": sectors}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching sectors: {str(e)}"
        )


@api.get("/stocks/sector/{sector}")
def get_stocks_by_sector_endpoint(
    sector: str,
    limit: Optional[int] = Query(
        None, ge=1, le=1000, description="Limit number of stocks"
    )
):
    """Get stocks by specific sector."""
    try:
        stocks = get_stocks_by_sector(sector, limit)
        return {"sector": sector, "count": len(stocks), "stocks": stocks}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stocks for sector {sector}: {str(e)}"
        )


@api.get("/stocks/stats")
def get_stock_stats():
    """Get database statistics."""
    try:
        stats = get_nifty_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching stats: {str(e)}"
        )


@api.get("/stocks/validate")
def validate_symbols_endpoint(
    symbols: str = Query(
        ..., description="Comma-separated ticker symbols to validate"
    )
):
    """Validate ticker symbols against database."""
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        valid_symbols, invalid_symbols = validate_nifty_symbols(symbol_list)
        return {
            "valid_symbols": valid_symbols,
            "invalid_symbols": invalid_symbols,
            "valid_count": len(valid_symbols),
            "invalid_count": len(invalid_symbols)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error validating symbols: {str(e)}"
        )


@api.get("/stocks/{symbol}")
def get_stock_by_symbol(symbol: str):
    """Get specific stock by symbol."""
    try:
        stock = stock_service.get_stock_by_symbol(symbol)
        if not stock:
            raise HTTPException(
                status_code=404, detail=f"Stock symbol {symbol} not found"
            )
        return stock
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching stock {symbol}: {str(e)}"
        )


# ---------- CLI ----------
def _cli() -> None:
    parser = argparse.ArgumentParser(description="Stock News Agent")

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(
        dest='command', help='Available commands'
    )

    # News command
    news_parser = subparsers.add_parser('news', help='Get news for tickers')
    news_parser.add_argument(
        "--tickers",
        required=True,
        help="Comma-separated tickers, e.g., RELIANCE,TCS",
    )
    news_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max items per source (1-100)",
    )
    news_parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Days back for Google News (1-30)",
    )
    news_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of pretty print",
    )

    # Stocks command
    stocks_parser = subparsers.add_parser(
        'stocks', help='List Nifty stocks from database'
    )
    stocks_parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of stocks to show",
    )
    stocks_parser.add_argument(
        "--sector",
        help="Filter by sector",
    )
    stocks_parser.add_argument(
        "--search",
        help="Search stocks by name or symbol",
    )
    stocks_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of pretty print",
    )

    # Sectors command
    sectors_parser = subparsers.add_parser(
        'sectors', help='List available sectors'
    )
    sectors_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of pretty print",
    )

    # Stats command
    stats_parser = subparsers.add_parser(
        'stats', help='Show database statistics'
    )
    stats_parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of pretty print",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize database for database-related commands
    if args.command in ['stocks', 'sectors', 'stats']:
        if not init_database():
            print("❌ Failed to initialize database")
            return

    if args.command == 'news':
        tickers = [
            t.strip().upper() for t in args.tickers.split(",") if t.strip()
        ]

        # Validate tickers against database
        valid_symbols, invalid_symbols = validate_nifty_symbols(tickers)
        if invalid_symbols:
            print(f"❌ Invalid ticker symbols: {', '.join(invalid_symbols)}")
            return

        articles = get_news(
            valid_symbols,
            per_source_limit=max(1, min(args.limit, 100)),
            google_days=max(1, min(args.days, 30)),
        )

        if args.json:
            print(
                json.dumps(
                    {
                        "tickers": valid_symbols,
                        "count": len(articles),
                        "articles": articles,
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(
                f"Tickers: {', '.join(valid_symbols)} | "
                f"Articles: {len(articles)}"
            )
            for a in articles:
                ts = a.get("published_iso") or ""
                sent = a.get("sentiment", {})
                comp = sent.get("compound", 0.0)
                print(
                    "- ",
                    a.get("source"),
                    "|",
                    ts,
                    "|",
                    a.get("ticker"),
                    "|",
                    f"{comp:+.3f}",
                )
                print("   ", a.get("title", "").strip())
                link = a.get("link", "")
                if link:
                    print("   ", link)

    elif args.command == 'stocks':
        if args.search:
            stocks = search_nifty_stocks(args.search, args.limit)
            title = f"Search results for '{args.search}'"
        elif args.sector:
            stocks = get_stocks_by_sector(args.sector, args.limit)
            title = f"Stocks in {args.sector} sector"
        else:
            stocks = get_nifty_stocks(args.limit)
            title = "Nifty Stocks"

        if args.json:
            print(json.dumps(
                {"count": len(stocks), "stocks": stocks}, ensure_ascii=False
            ))
        else:
            print(f"{title} ({len(stocks)} stocks)")
            for stock in stocks:
                print(f"  {stock['symbol']}: {stock['name']} "
                      f"({stock['sector']})")

    elif args.command == 'sectors':
        sectors = get_nifty_sectors()
        if args.json:
            print(json.dumps(
                {"count": len(sectors), "sectors": sectors}, ensure_ascii=False
            ))
        else:
            print(f"Available sectors ({len(sectors)} total):")
            for sector in sectors:
                print(f"  - {sector}")

    elif args.command == 'stats':
        stats = get_nifty_stats()
        if args.json:
            print(json.dumps(stats, ensure_ascii=False))
        else:
            print("📊 Database Statistics:")
            print(f"  Total stocks: {stats['total_stocks']}")
            print(f"  Total sectors: {len(stats['sectors'])}")
            print("\n📈 Stocks by sector:")
            for sector, count in stats['stocks_by_sector'].items():
                print(f"  {sector}: {count} stocks")


if __name__ == "__main__":
    _cli()
