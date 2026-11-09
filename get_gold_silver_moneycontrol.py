"""
Fetch Gold and Silver prices from Moneycontrol.

Usage:
    python get_gold_silver_moneycontrol.py

Sources:
    Gold: https://www.moneycontrol.com/markets/gold-price
    Silver: https://www.moneycontrol.com/markets/silver-rates
"""

from __future__ import annotations

import re
import time
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


GOLD_URL = "https://www.moneycontrol.com/markets/gold-price"
SILVER_URL = "https://www.moneycontrol.com/markets/silver-rates"
GREEN = "\033[32m"
RESET = "\033[0m"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


@dataclass
class PreciousMetalQuote:
    """Precious metal quote from Moneycontrol."""

    name: str
    last: float
    change: float | None = None
    change_pct: float | None = None
    prev_close: float | None = None
    open_: float | None = None
    high: float | None = None
    low: float | None = None
    unit: str = "per 10g"  # gold in INR per 10g, silver in INR per kg
    source: str = "moneycontrol"
    raw: dict[str, Any] | None = None

    def __str__(self) -> str:
        if self.unit == "per 10g":
            last_str = f"{GREEN}₹{self.last:,.2f}{RESET} per 10g"
        else:
            last_str = f"{GREEN}₹{self.last:,.2f}{RESET} per kg"
        
        parts = [f"{self.name}: {last_str}"]
        if self.change is not None:
            pct = f" ({self.change_pct:+.2f}%)" if self.change_pct is not None else ""
            parts.append(f" | Change: ₹{self.change:+.2f}{pct}")
        return "".join(parts)


def _fetch_html_with_retry(url: str, max_retries: int = MAX_RETRIES, delay: int = RETRY_DELAY) -> str:
    """Fetch HTML content from the given URL with retry logic."""
    if httpx is None:
        raise RuntimeError("Install httpx: pip install httpx")
    
    last_error = None
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                r = client.get(url, headers={"User-Agent": USER_AGENT})
                r.raise_for_status()
                return r.text
        except httpx.HTTPStatusError as e:
            last_error = e
            if e.response.status_code == 503:
                # Server unavailable - retry after delay
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    continue
            raise RuntimeError(
                f"HTTP error {e.response.status_code} for URL {url}. "
                "The server may be temporarily unavailable."
            ) from e
        except httpx.RequestError as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(delay)
                continue
            raise RuntimeError(f"Request failed for URL {url}: {e}") from e
    
    if last_error:
        raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts") from last_error
    raise RuntimeError(f"Failed to fetch {url}")


def _parse_number(s: str) -> float | None:
    """Parse a number from a string, handling commas and currency symbols."""
    s = s.replace(",", "").replace("₹", "").replace("Rs", "").strip()
    m = re.match(r"([+-]?\d+\.?\d*)", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _extract_gold_from_html(html: str) -> PreciousMetalQuote | None:
    """Extract gold price from Moneycontrol HTML."""
    if BeautifulSoup is None:
        return None
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Initialize values
    last: float | None = None
    prev_close: float | None = None
    open_: float | None = None
    high: float | None = None
    low: float | None = None
    change: float | None = None
    change_pct: float | None = None
    
    # Look for the gold price in various places
    # Method 1: Find price in specific elements
    price_elements = soup.find_all(['span', 'div', 'p'], class_=lambda x: x and 'price' in x.lower() if x else False)
    
    for elem in price_elements:
        text = elem.get_text()
        val = _parse_number(text)
        if val and val > 1000 and last is None:  # Gold is typically > 5000 INR per 10g
            last = val
            break
    
    # Method 2: Look for the main price container
    if last is None:
        # Look for data in script tags or specific patterns
        script_text = str(soup.find_all('script'))
        m = re.search(r'["\']?price["\']?\s*[=:]\s*["\']?([\d,]+\.?\d*)["\']?', script_text)
        if m:
            last = float(m.group(1).replace(",", ""))
    
    # Method 3: Search in all text for price patterns
    if last is None:
        text = soup.get_text()
        # Gold price pattern: look for ₹XX,XXX.XX or Rs X,XXX.XX per 10g
        m = re.search(r'[₹Rs\.]\s*([5-9]\d{2,3}[,\.]\d{2})', text)
        if m:
            last = float(m.group(1).replace(",", ""))
    
    # Extract price change
    text = soup.get_text()
    m = re.search(r'([+-]?\d{1,3}[,\.]\d{2})\s*\(([+-]?\d{1,2}[,\.]\d{2})%\)', text)
    if m:
        change = float(m.group(1).replace(",", ""))
        change_pct = float(m.group(2).replace(",", ""))
    
    # Extract high/low
    m = re.search(r'[Hh]igh[:\s]*[₹Rs\.]\s*([\d,]+\.?\d*)', text)
    if m:
        high = float(m.group(1).replace(",", ""))
    
    m = re.search(r'[Ll]ow[:\s]*[₹Rs\.]\s*([\d,]+\.?\d*)', text)
    if m:
        low = float(m.group(1).replace(",", ""))
    
    # Extract open
    m = re.search(r'[Oo]pen[:\s]*[₹Rs\.]\s*([\d,]+\.?\d*)', text)
    if m:
        open_ = float(m.group(1).replace(",", ""))
    
    # Extract previous close
    m = re.search(r'[Pp]revious\s*[Cc]lose[:\s]*[₹Rs\.]\s*([\d,]+\.?\d*)', text)
    if m:
        prev_close = float(m.group(1).replace(",", ""))
    
    if last is None:
        return None
    
    # Calculate change from prev_close if not found
    if change is None and prev_close:
        change = last - prev_close
        if prev_close:
            change_pct = (change / prev_close) * 100
    
    raw = {
        "last": last,
        "change": change,
        "change_pct": change_pct,
        "prev_close": prev_close,
        "open": open_,
        "high": high,
        "low": low,
    }
    
    return PreciousMetalQuote(
        name="Gold (MC)",
        last=last,
        change=change,
        change_pct=change_pct,
        prev_close=prev_close,
        open_=open_,
        high=high,
        low=low,
        unit="per 10g",
        source="moneycontrol",
        raw=raw,
    )


def _extract_silver_from_html(html: str) -> PreciousMetalQuote | None:
    """Extract silver price from Moneycontrol HTML."""
    if BeautifulSoup is None:
        return None
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Initialize values
    last: float | None = None
    prev_close: float | None = None
    open_: float | None = None
    high: float | None = None
    low: float | None = None
    change: float | None = None
    change_pct: float | None = None
    
    # Look for the silver price in various places
    price_elements = soup.find_all(['span', 'div', 'p'], class_=lambda x: x and 'price' in x.lower() if x else False)
    
    for elem in price_elements:
        text = elem.get_text()
        val = _parse_number(text)
        if val and 1000 < val < 200000 and last is None:  # Silver per kg in INR is typically 50000-150000
            last = val
            break
    
    # Method 2: Look for the main price container
    if last is None:
        script_text = str(soup.find_all('script'))
        m = re.search(r'["\']?price["\']?\s*[=:]\s*["\']?([\d,]+\.?\d*)["\']?', script_text)
        if m:
            last = float(m.group(1).replace(",", ""))
    
    # Method 3: Search in all text for price patterns (Silver per kg)
    if last is None:
        text = soup.get_text()
        # Silver per kg pattern: ₹XX,XXX.XX
        m = re.search(r'[₹Rs\.]\s*([5-8]\d{1,3}[,\.]\d{2})', text)
        if m:
            last = float(m.group(1).replace(",", ""))
    
    # Extract price change
    text = soup.get_text()
    m = re.search(r'([+-]?\d{1,3}[,\.]\d{2})\s*\(([+-]?\d{1,2}[,\.]\d{2})%\)', text)
    if m:
        change = float(m.group(1).replace(",", ""))
        change_pct = float(m.group(2).replace(",", ""))
    
    # Extract high/low
    m = re.search(r'[Hh]igh[:\s]*[₹Rs\.]\s*([\d,]+\.?\d*)', text)
    if m:
        high = float(m.group(1).replace(",", ""))
    
    m = re.search(r'[Ll]ow[:\s]*[₹Rs\.]\s*([\d,]+\.?\d*)', text)
    if m:
        low = float(m.group(1).replace(",", ""))
    
    # Extract open
    m = re.search(r'[Oo]pen[:\s]*[₹Rs\.]\s*([\d,]+\.?\d*)', text)
    if m:
        open_ = float(m.group(1).replace(",", ""))
    
    # Extract previous close
    m = re.search(r'[Pp]revious\s*[Cc]lose[:\s]*[₹Rs\.]\s*([\d,]+\.?\d*)', text)
    if m:
        prev_close = float(m.group(1).replace(",", ""))
    
    if last is None:
        return None
    
    # Calculate change from prev_close if not found
    if change is None and prev_close:
        change = last - prev_close
        if prev_close:
            change_pct = (change / prev_close) * 100
    
    raw = {
        "last": last,
        "change": change,
        "change_pct": change_pct,
        "prev_close": prev_close,
        "open": open_,
        "high": high,
        "low": low,
    }
    
    return PreciousMetalQuote(
        name="Silver (MC)",
        last=last,
        change=change,
        change_pct=change_pct,
        prev_close=prev_close,
        open_=open_,
        high=high,
        low=low,
        unit="per kg",
        source="moneycontrol",
        raw=raw,
    )


def get_gold_price() -> PreciousMetalQuote:
    """
    Fetch Gold price from Moneycontrol.

    Returns:
        PreciousMetalQuote with gold price in INR per 10g

    Raises:
        RuntimeError: If fetch or parse fails.
    """
    html = _fetch_html_with_retry(GOLD_URL)
    gold = _extract_gold_from_html(html)
    
    if gold is None:
        raise RuntimeError(
            "Could not extract Gold price from Moneycontrol. "
            "The page structure may have changed."
        )
    return gold


def get_silver_price() -> PreciousMetalQuote:
    """
    Fetch Silver price from Moneycontrol.

    Returns:
        PreciousMetalQuote with silver price in INR per kg

    Raises:
        RuntimeError: If fetch or parse fails.
    """
    html = _fetch_html_with_retry(SILVER_URL)
    silver = _extract_silver_from_html(html)
    
    if silver is None:
        raise RuntimeError(
            "Could not extract Silver price from Moneycontrol. "
            "The page structure may have changed."
        )
    return silver


def get_gold_silver() -> tuple[PreciousMetalQuote, PreciousMetalQuote]:
    """
    Fetch both Gold and Silver prices from Moneycontrol.

    Returns:
        (gold_quote, silver_quote)

    Raises:
        RuntimeError: If fetch or parse fails.
    """
    gold = get_gold_price()
    silver = get_silver_price()
    return gold, silver


def main() -> None:
    print("Fetching Gold price from Moneycontrol...")
    print("Source:", GOLD_URL)
    try:
        gold = get_gold_price()
        print()
        print(gold)
        print()
        if gold.raw:
            print("Gold Details:")
            for k, v in gold.raw.items():
                if isinstance(v, float):
                    val = f"{GREEN}₹{v:,.2f}{RESET}" if k == "last" else f"₹{v:,.2f}"
                    print(f"  {k}: {val}")
                else:
                    print(f"  {k}: {v}")
    except Exception as e:
        print(f"Error fetching gold: {e}")
    
    print()
    print("Fetching Silver price from Moneycontrol...")
    print("Source:", SILVER_URL)
    try:
        silver = get_silver_price()
        print()
        print(silver)
        print()
        if silver.raw:
            print("Silver Details:")
            for k, v in silver.raw.items():
                if isinstance(v, float):
                    val = f"{GREEN}₹{v:,.2f}{RESET}" if k == "last" else f"₹{v:,.2f}"
                    print(f"  {k}: {val}")
                else:
                    print(f"  {k}: {v}")
    except Exception as e:
        print(f"Error fetching silver: {e}")


if __name__ == "__main__":
    main()

