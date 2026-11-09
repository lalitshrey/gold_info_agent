from __future__ import annotations

import asyncio
from typing import List
import httpx
import feedparser
from dateutil import parser as date_parser

from ..models import NewsItem, Source


def yahoo_rss_url(ticker: str) -> str:
	return f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"


async def fetch_ticker(client: httpx.AsyncClient, ticker: str) -> List[NewsItem]:
	url = yahoo_rss_url(ticker)
	source = Source(name=f"Yahoo Finance: {ticker}")
	items: List[NewsItem] = []
	try:
		resp = await client.get(url, timeout=15)
		resp.raise_for_status()
		parsed = feedparser.parse(resp.content)
		for entry in parsed.entries:
			title = str(entry.get("title", ""))
			link = str(entry.get("link", ""))
			summary = str(entry.get("summary", "")) if entry.get("summary") else None
			published_at = None
			if entry.get("published"):
				try:
					published_at = date_parser.parse(str(entry.get("published")))
				except Exception:
					published_at = None
			item = NewsItem(
				id=link or title,
				title=title,
				url=link,
				summary=summary,
				published_at=published_at,
				source=source,
				tickers=[ticker.upper()],
			)
			item.ensure_timezone()
			items.append(item)
	except Exception:
		return []
	return items


async def fetch_yahoo(tickers: List[str]) -> List[NewsItem]:
	if not tickers:
		return []
	async with httpx.AsyncClient(headers={"User-Agent": "stock-news-agent/1.0"}) as client:
		tasks = [fetch_ticker(client, t.upper()) for t in tickers]
		results = await asyncio.gather(*tasks, return_exceptions=True)
		items: List[NewsItem] = []
		for res in results:
			if isinstance(res, Exception):
				continue
			items.extend(res)
		return items
