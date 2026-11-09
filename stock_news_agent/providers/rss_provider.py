from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Iterable, List
import feedparser
import httpx
from dateutil import parser as date_parser

from ..models import NewsItem, Source


DEFAULT_RSS_FEEDS: List[str] = [
	"https://feeds.a.dj.com/rss/RSSMarketsMain.xml", # WSJ Markets
	"https://www.investing.com/rss/news_25.rss",    # Investing.com Stock Market News
	"https://www.marketwatch.com/feeds/topstories",  # MarketWatch Top Stories
	# Added India-focused sources
	"https://www.business-standard.com/rss/markets-106.rss",  # Business Standard - Markets
	"https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",  # Economic Times - Markets
	"https://www.moneycontrol.com/rss/MCtopnews.xml",  # Moneycontrol - Top News
	"https://www.nseindia.com/content/RSS/press_releases.xml",  # NSE India - Press Releases (RSS)
]


async def fetch_feed(client: httpx.AsyncClient, feed_url: str) -> List[NewsItem]:
	source = Source(name=feed_url, url=feed_url)  # name defaults to URL; will be replaced by feed title if present
	items: List[NewsItem] = []
	try:
		resp = await client.get(feed_url, timeout=15)
		resp.raise_for_status()
		parsed = feedparser.parse(resp.content)
		if parsed.feed.get("title"):
			source = Source(name=str(parsed.feed.get("title")), url=feed_url)
		for entry in parsed.entries:
			title = str(entry.get("title", ""))
			link = str(entry.get("link", ""))
			summary = str(entry.get("summary", "")) if entry.get("summary") else None
			published_at: datetime | None = None
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
				tickers=[],
			)
			item.ensure_timezone()
			items.append(item)
	except Exception:
		# ignore individual feed failures
		return []
	return items


async def fetch_rss(feeds: Iterable[str] | None = None) -> List[NewsItem]:
	feed_urls = list(feeds) if feeds else DEFAULT_RSS_FEEDS
	async with httpx.AsyncClient(headers={"User-Agent": "stock-news-agent/1.0"}) as client:
		tasks = [fetch_feed(client, url) for url in feed_urls]
		results = await asyncio.gather(*tasks, return_exceptions=True)
		items: List[NewsItem] = []
		for res in results:
			if isinstance(res, Exception):
				continue
			items.extend(res)
		return items
