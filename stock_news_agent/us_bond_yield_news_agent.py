import argparse
import datetime as dt
import html as html_lib
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional


_BASE_DIR = Path(__file__).resolve().parent
_DEFAULT_OUTPUT = _BASE_DIR / "bond_yield_news.json"

_TAGS_RE = re.compile(r"<[^>]+>")


def _strip_html(value: Optional[str]) -> str:
    if not value:
        return ""
    return _TAGS_RE.sub("", html_lib.unescape(str(value))).strip()


def _to_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        if isinstance(value, dt.datetime):
            dt_value = value
        else:
            dt_value = dt.datetime(*value[:6])
        if dt_value.tzinfo is None:
            dt_value = dt_value.replace(tzinfo=dt.timezone.utc)
        return dt_value.isoformat()
    except Exception:
        return None


def _build_queries() -> List[str]:
    return [
        "US Treasury yield",
        "10 year Treasury yield",
        "2 year Treasury yield",
        "30 year Treasury yield",
        "US bond yield",
        "US government bond yield",
        "long bond yield",
        "Treasury yield curve",
        "Fed bond yield",
    ]


def fetch_google_news(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    query_enc = urllib.parse.quote_plus(query)
    url = (
        "https://news.google.com/rss/search?"
        f"q={query_enc}&hl=en-US&gl=US&ceid=US:en"
    )
    articles: List[Dict[str, Any]] = []
    seen: set[str] = set()

    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            xml_text = response.read().decode("utf-8", errors="replace")
    except Exception:
        return articles

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return articles

    for item in root.findall("./channel/item")[:limit]:
        title = _strip_html(item.findtext("title", default=""))
        link = item.findtext("link", default="")
        summary = _strip_html(item.findtext("description", default=""))
        pub_date = item.findtext("pubDate", default="")
        key = (link or title).strip()
        if not key or key in seen:
            continue
        seen.add(key)

        published = None
        if pub_date:
            try:
                published = dt.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
            except ValueError:
                try:
                    published = dt.datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S GMT")
                except ValueError:
                    published = None

        articles.append(
            {
                "title": title,
                "summary": summary,
                "link": link,
                "source": "Google News",
                "query": query,
                "published": _to_iso(published),
                "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
        )

    return articles


def fetch_bond_yield_news(limit_per_query: int = 10) -> List[Dict[str, Any]]:
    collected: List[Dict[str, Any]] = []
    for query in _build_queries():
        collected.extend(fetch_google_news(query, limit=limit_per_query))

    seen: set[str] = set()
    unique: List[Dict[str, Any]] = []
    for article in collected:
        key = (article.get("link") or article.get("title") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(article)

    unique.sort(
        key=lambda x: x.get("published") or "1970-01-01T00:00:00+00:00",
        reverse=True,
    )
    return unique


def fetch_us_bond_yields() -> Dict[str, float]:
    symbols = {
        "US 1Y": "^IRX",
        "US 2Y": "^FVX",
        "US 5Y": "^FVX",
        "US 10Y": "^TNX",
    }
    results: Dict[str, float] = {}

    for label, symbol in symbols.items():
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8", errors="replace"))
            result = data.get("chart", {}).get("result", [{}])[0]
            meta = result.get("meta", {})
            value = meta.get("regularMarketPrice")
            if value is not None:
                results[label] = float(value)
        except Exception:
            continue

    return results


def run_once(output_file: str | Path = _DEFAULT_OUTPUT, limit_per_query: int = 10) -> Dict[str, Any]:
    payload = {
        "agent": "us_bond_yield_news_agent",
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "count": 0,
        "articles": [],
        "bond_yields": {},
    }

    articles = fetch_bond_yield_news(limit_per_query=limit_per_query)
    payload["count"] = len(articles)
    payload["articles"] = articles
    payload["bond_yields"] = fetch_us_bond_yields()

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("U.S. Treasury bond yields:")
    yields = payload["bond_yields"]
    if yields:
        for label, value in yields.items():
            print(f"- {label}: {value:.3f}%")
    else:
        print("- No live yield data available right now")

    print(f"\nFetched {len(articles)} U.S. bond-yield news items")
    for article in articles[:5]:
        print(f"- {article.get('title')} | {article.get('source')} | {article.get('published')}")
    return payload


def run_every_hour(interval_hours: float = 1.0, output_file: str | Path = _DEFAULT_OUTPUT, limit_per_query: int = 10) -> None:
    interval_seconds = max(60.0, float(interval_hours) * 3600.0)
    while True:
        run_once(output_file=output_file, limit_per_query=limit_per_query)
        print(f"Sleeping for {interval_hours:.0f} hour(s)...")
        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hourly U.S. bond-yield news agent")
    parser.add_argument("--run-once", action="store_true", help="Fetch once and exit")
    parser.add_argument("--interval-hours", type=float, default=1.0, help="Repeat interval in hours")
    parser.add_argument("--limit-per-query", type=int, default=10, help="Max items per Google News query")
    parser.add_argument("--output", type=str, default=str(_DEFAULT_OUTPUT), help="JSON output file path")
    args = parser.parse_args()

    if args.run_once:
        run_once(output_file=args.output, limit_per_query=args.limit_per_query)
        return

    run_every_hour(
        interval_hours=args.interval_hours,
        output_file=args.output,
        limit_per_query=args.limit_per_query,
    )


if __name__ == "__main__":
    main()
