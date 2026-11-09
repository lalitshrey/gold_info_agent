"""
Fetch COMEX Gold and Silver prices from comexlive.org.

Usage:
    python get_gold_silver_comexlive.py

Source: https://comexlive.org/
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore


URL = "https://comexlive.org/"
GREEN = "\033[32m"
RESET = "\033[0m"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class CommodityQuote:
    """COMEX commodity quote (Gold or Silver)."""

    name: str
    last: float
    change: float | None = None
    change_pct: float | None = None
    close: float | None = None
    high: float | None = None
    low: float | None = None
    last_trade: str | None = None
    source: str = "comexlive.org"
    raw: dict[str, Any] | None = None

    def __str__(self) -> str:
        last_str = f"{GREEN}{self.last:,.2f}{RESET}" if "gold" in self.name.lower() else f"{GREEN}{self.last:.3f}{RESET}"
        parts = [f"{self.name}: {last_str}"]
        if self.change is not None:
            pct = f" ({self.change_pct:+.2f}%)" if self.change_pct is not None else ""
            parts.append(f" | Change: {self.change:+.2f}{pct}")
        if self.last_trade:
            parts.append(f" | {self.last_trade}")
        return "".join(parts)


def _fetch_html() -> str:
    if httpx is None:
        raise RuntimeError("Install httpx: pip install httpx")
    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        r = client.get(URL, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        return r.text


def _parse_number(s: str) -> float | None:
    s = s.replace(",", "").strip()
    m = re.match(r"([+-]?\d+\.?\d*)", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _extract_via_bs4(html: str) -> tuple[CommodityQuote | None, CommodityQuote | None]:
    """Extract Gold and Silver from COMEX Live table using BeautifulSoup."""
    if BeautifulSoup is None:
        return None, None
    soup = BeautifulSoup(html, "html.parser")
    gold: CommodityQuote | None = None
    silver: CommodityQuote | None = None

    # Find all table rows
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 6:
            continue
        first_text = (cells[0].get_text() or "").strip()
        if "COMEX Gold" not in first_text and "COMEX Silver" not in first_text:
            continue

        # Cells: Symbol | Last | Change | Change % | Close | High | Low | Last Trade
        values: list[float | str | None] = []
        for i, c in enumerate(cells[1:], start=1):
            t = (c.get_text() or "").strip()
            if i <= 6:
                v = _parse_number(t)
                values.append(v if v is not None else t)
            else:
                values.append(t if t else None)

        while len(values) < 8:
            values.append(None)
        last = values[0]
        change = values[1] if isinstance(values[1], (int, float)) else None
        change_pct = values[2] if isinstance(values[2], (int, float)) else None
        close = values[3] if isinstance(values[3], (int, float)) else None
        high = values[4] if isinstance(values[4], (int, float)) else None
        low = values[5] if isinstance(values[5], (int, float)) else None
        last_trade = values[7] if isinstance(values[7], str) else None

        if last is None or not isinstance(last, (int, float)):
            continue
        raw: dict[str, Any] = {
            "last": last,
            "change": change,
            "change_pct": change_pct,
            "close": close,
            "high": high,
            "low": low,
            "last_trade": last_trade,
        }
        q = CommodityQuote(
            name="COMEX Gold" if "Gold" in first_text else "COMEX Silver",
            last=float(last),
            change=float(change) if change is not None else None,
            change_pct=float(change_pct) if change_pct is not None else None,
            close=float(close) if close is not None else None,
            high=float(high) if high is not None else None,
            low=float(low) if low is not None else None,
            last_trade=last_trade,
            source="comexlive.org",
            raw=raw,
        )
        if "Gold" in first_text:
            gold = q
        else:
            silver = q

    return gold, silver


def _extract_via_regex(html: str) -> tuple[CommodityQuote | None, CommodityQuote | None]:
    """Fallback: extract Gold and Silver using regex on raw HTML."""
    gold: CommodityQuote | None = None
    silver: CommodityQuote | None = None

    # Pattern: COMEX Gold|4,601.10|-22.60|-0.49%|4,621.60|4,625.50|4,539.10|18-Jan 03:18
    # Or similar with various delimiters
    gold_match = re.search(
        r"COMEX\s+Gold[^|]*\|([\d,]+\.?\d*)\|([+-]?\d+\.?\d*)\|([+-]?\d+\.?\d*%?)\|([\d,]+\.?\d*)\|([\d,]+\.?\d*)\|([\d,]+\.?\d*)\|([^|]+)",
        html,
        re.I,
    )
    silver_match = re.search(
        r"COMEX\s+Silver[^|]*\|([\d,]+\.?\d*)\|([+-]?\d+\.?\d*)\|([+-]?\d+\.?\d*%?)\|([\d,]+\.?\d*)\|([\d,]+\.?\d*)\|([\d,]+\.?\d*)\|([^|]+)",
        html,
        re.I,
    )

    def _make_quote(name: str, m: re.Match[str]) -> CommodityQuote:
        last = float(m.group(1).replace(",", ""))
        change = float(m.group(2).replace(",", ""))
        ch_pct_s = m.group(3).replace("%", "").strip()
        change_pct = float(ch_pct_s) if ch_pct_s else None
        close = float(m.group(4).replace(",", ""))
        high = float(m.group(5).replace(",", ""))
        low = float(m.group(6).replace(",", ""))
        last_trade = m.group(7).strip()
        raw = {
            "last": last,
            "change": change,
            "change_pct": change_pct,
            "close": close,
            "high": high,
            "low": low,
            "last_trade": last_trade,
        }
        return CommodityQuote(
            name=name,
            last=last,
            change=change,
            change_pct=change_pct,
            close=close,
            high=high,
            low=low,
            last_trade=last_trade,
            source="comexlive.org",
            raw=raw,
        )

    if gold_match:
        gold = _make_quote("COMEX Gold", gold_match)
    if silver_match:
        silver = _make_quote("COMEX Silver", silver_match)

    return gold, silver


def get_gold_silver() -> tuple[CommodityQuote, CommodityQuote]:
    """
    Fetch COMEX Gold and Silver prices from comexlive.org.

    Returns:
        (gold_quote, silver_quote)

    Raises:
        RuntimeError: If fetch or parse fails.
    """
    html = _fetch_html()
    gold, silver = None, None

    if BeautifulSoup is not None:
        gold, silver = _extract_via_bs4(html)
    if gold is None or silver is None:
        g2, s2 = _extract_via_regex(html)
        if gold is None:
            gold = g2
        if silver is None:
            silver = s2

    if gold is None or silver is None:
        raise RuntimeError(
            "Could not extract Gold and/or Silver from comexlive.org. "
            "The page structure may have changed."
        )
    return gold, silver


def main() -> None:
    print("Fetching Gold & Silver from comexlive.org...")
    print("Source:", URL)
    try:
        gold, silver = get_gold_silver()
        print()
        print(gold)
        print(silver)
        print()
        for q in (gold, silver):
            if q.raw:
                print(f"{q.name} details:")
                for k, v in q.raw.items():
                    if v is None:
                        print(f"  {k}: -")
                    elif isinstance(v, float):
                        val = f"{GREEN}{v:,.2f}{RESET}" if k == "last" else f"{v:,.2f}"
                        print(f"  {k}: {val}")
                    else:
                        print(f"  {k}: {v}")
                print()
    except Exception as e:
        print(f"Error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
