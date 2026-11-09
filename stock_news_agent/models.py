from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, Field


class Source(BaseModel):
	name: str = Field(..., description="Human readable source name")
	url: Optional[HttpUrl] = Field(None, description="Source homepage URL")


class NewsItem(BaseModel):
	id: str = Field(..., description="Stable identifier for deduplication")
	title: str
	url: HttpUrl
	summary: Optional[str] = None
	published_at: Optional[datetime] = None
	source: Source
	tickers: List[str] = Field(default_factory=list)

	def sort_key(self) -> float:
		if self.published_at is None:
			return 0.0
		return self.published_at.timestamp()

	def ensure_timezone(self) -> None:
		if self.published_at and self.published_at.tzinfo is None:
			self.published_at = self.published_at.replace(tzinfo=timezone.utc)
