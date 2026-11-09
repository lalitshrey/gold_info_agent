from __future__ import annotations

import asyncio
import argparse
import json
from typing import List
from rich.console import Console
from rich.table import Table

from .aggregator import merge_filter_sort
from .providers.rss_provider import fetch_rss
from .providers.yahoo_provider import fetch_yahoo


async def run(tickers: List[str], minutes: int, limit: int) -> List[dict]:
	# Fetch from providers concurrently
	rss_items_task = asyncio.create_task(fetch_rss())
	yahoo_items_task = asyncio.create_task(fetch_yahoo(tickers))
	rss_items, yahoo_items = await asyncio.gather(rss_items_task, yahoo_items_task)
	merged = merge_filter_sort(rss_items + yahoo_items, lookback_minutes=minutes, limit=limit)
	# Convert to dicts for output
	return [
		{
			"title": it.title,
			"url": str(it.url),
			"summary": it.summary,
			"published_at": it.published_at.isoformat() if it.published_at else None,
			"source": it.source.name,
			"tickers": it.tickers,
		}
		for it in merged
	]


def print_rich(rows: List[dict]) -> None:
	console = Console()
	table = Table(show_lines=False)
	table.add_column("Time", no_wrap=True)
	table.add_column("Source", no_wrap=True)
	table.add_column("Title")
	table.add_column("Tickers", no_wrap=True)
	for row in rows:
		time_str = row["published_at"] or ""
		tickers_str = ",".join(row.get("tickers") or [])
		table.add_row(time_str, row["source"], f"[link={row['url']}]" + row["title"] + "[/link]", tickers_str)
	console.print(table)


def main() -> None:
	parser = argparse.ArgumentParser(description="Stock News Agent")
	parser.add_argument("tickers", nargs="*", help="Ticker symbols like AAPL MSFT TSLA")
	parser.add_argument("--minutes", type=int, default=1440, help="Lookback window in minutes")
	parser.add_argument("--limit", type=int, default=50, help="Maximum items to show")
	parser.add_argument("--format", choices=["rich", "json"], default="rich", help="Output format")
	args = parser.parse_args()

	rows = asyncio.run(run([t.upper() for t in args.tickers], args.minutes, args.limit))
	if args.format == "json":
		print(json.dumps(rows, indent=2))
	else:
		print_rich(rows)


if __name__ == "__main__":
	main()
