from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Dict

from .models import NewsItem


def _dedupe(items: Iterable[NewsItem]) -> List[NewsItem]:
	seen: Dict[str, NewsItem] = {}
	for it in items:
		key = it.id or it.url
		if key not in seen:
			seen[key] = it
	return list(seen.values())


def merge_filter_sort(
	items: List[NewsItem],
	lookback_minutes: int = 1440,
	limit: int = 50,
) -> List[NewsItem]:
	cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
	for it in items:
		it.ensure_timezone()
	filtered = [it for it in items if it.published_at is None or it.published_at >= cutoff]
	deduped = _dedupe(filtered)
	sorted_items = sorted(deduped, key=lambda i: i.sort_key(), reverse=True)
	return sorted_items[:limit]
