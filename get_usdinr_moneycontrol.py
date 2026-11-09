"""
Fetch USD/INR (US Dollar to Indian Rupee) exchange rate from Moneycontrol.

Usage:
    python get_usdinr_moneycontrol.py

Source: https://www.moneycontrol.com/markets/currencies/usd-inr/
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


URL = "https://www.moneycontrol.com/markets/currencies/usd-inr/"
GREEN = "\033[32m"
RESET = "\033[0m"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class UsdInrQuote:
    """USD/INR quote from Moneycontrol."""

    rate: float
    bid: float | None = None
    ask: float | None = None
    prev_close: float | None = None
    open_: float | None = None
    high: float | None = None
    low: float | None = None
    change: float | None = None
    change_pct: float | None = None
    source: str = "moneycontrol"
    raw: dict[str, Any] | None = None

    def __str__(self) -> str:
        rate_str = f"{GREEN}{self.rate:.4f}{RESET}"
        parts = [f"USD/INR = {rate_str}"]
        if self.bid is not None and self.ask is not None:
            parts.append(f" (Bid/Ask: {self.bid:.4f} / {self.ask:.4f})")
        if self.change is not None:
            pct = f" ({self.change_pct:+.2f}%)" if self.change_pct is not None else ""
            parts.append(f" | Change: {self.change:+.4f}{pct}")
        return "".join(parts)


def _fetch_html() -> str:
    if httpx is None:
        raise RuntimeError("Install httpx: pip install httpx")
    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        r = client.get(URL, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        return r.text


def _extract_via_regex(html: str) -> dict[str, float] | None:
    """Extract rates using regex patterns on raw HTML."""
    out: dict[str, float] = {}
    # Bid/Ask pattern (e.g. 91.8650/91.8950)
    m = re.search(r"(\d{2}\.\d{4})/(\d{2}\.\d{4})", html)
    if m:
        out["bid"], out["ask"] = float(m.group(1)), float(m.group(2))
        out["rate"] = (out["bid"] + out["ask"]) / 2
    # Previous Close|91.6475|
    m = re.search(r"Previous\s+Close\b[^|]*\|(\d+\.\d+)\|", html, re.I)
    if m:
        out["prev_close"] = float(m.group(1))
    # Open|91.5600|
    m = re.search(r"\bOpen\s*\|(\d+\.\d+)\|", html, re.I)
    if m:
        out["open"] = float(m.group(1))
    # High|92.0125|
    m = re.search(r"\bHigh\s*\|(\d+\.\d+)\|", html, re.I)
    if m:
        out["high"] = float(m.group(1))
    # Low|91.4175|
    m = re.search(r"\bLow\s*\|(\d+\.\d+)\|", html, re.I)
    if m:
        out["low"] = float(m.group(1))
    # Change: 0.2175(0.24%) or similar
    m = re.search(r"(-?\d+\.\d+)\s*\(\s*(-?\d+\.?\d*)\s*%\)", html)
    if m:
        out["change"] = float(m.group(1))
        out["change_pct"] = float(m.group(2))
    if not out:
        return None
    if "rate" not in out and "prev_close" in out:
        out["rate"] = out["prev_close"]
    return out


def _extract_via_bs4(html: str) -> dict[str, float] | None:
    """Extract rates using BeautifulSoup (tables, data attributes, etc.)."""
    if BeautifulSoup is None:
        return None
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, float] = {}

    # Look for table rows with Open, High, Low, Previous Close
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        label = (cells[0].get_text() or "").strip().lower()
        val_text = (cells[-1].get_text() or "").strip()
        m = re.match(r"[\d,]+\.?\d*", val_text.replace(",", ""))
        if not m:
            continue
        try:
            v = float(m.group(0).replace(",", ""))
        except ValueError:
            continue
        if "open" in label and "interest" not in label:
            out["open"] = v
        elif "high" in label:
            out["high"] = v
        elif "low" in label:
            out["low"] = v
        elif "previous" in label or "prev" in label:
            out["prev_close"] = v
        elif "vwap" in label:
            out["vwap"] = v

    # Bid/Ask in text
    text = soup.get_text()
    m = re.search(r"(\d{2}\.\d{4})/(\d{2}\.\d{4})", text)
    if m:
        out["bid"] = float(m.group(1))
        out["ask"] = float(m.group(2))
        out["rate"] = (out["bid"] + out["ask"]) / 2

    if "rate" not in out and "prev_close" in out:
        out["rate"] = out["prev_close"]
    if "rate" not in out and "vwap" in out:
        out["rate"] = out["vwap"]
    return out if out else None


def get_usdinr() -> UsdInrQuote:
    """
    Fetch USD/INR rate from Moneycontrol.

    Returns:
        UsdInrQuote with rate, bid, ask, prev_close, etc.

    Raises:
        RuntimeError: If fetch or parse fails.
    """
    html = _fetch_html()
    data: dict[str, float] | None = None

    if BeautifulSoup is not None:
        data = _extract_via_bs4(html)
    if data is None:
        data = _extract_via_regex(html)

    if not data or "rate" not in data:
        raise RuntimeError(
            "Could not extract USD/INR from Moneycontrol. "
            "The page structure may have changed."
        )

    return UsdInrQuote(
        rate=data["rate"],
        bid=data.get("bid"),
        ask=data.get("ask"),
        prev_close=data.get("prev_close"),
        open_=data.get("open"),
        high=data.get("high"),
        low=data.get("low"),
        change=data.get("change"),
        change_pct=data.get("change_pct"),
        source="moneycontrol",
        raw={k: v for k, v in data.items() if k != "vwap"},
    )


def main() -> None:
    print("Fetching USD/INR from Moneycontrol...")
    print("Source:", URL)
    try:
        q = get_usdinr()
        print()
        print(q)
        print()
        if q.raw:
            print("Details:")
            for k, v in q.raw.items():
                if isinstance(v, float):
                    val = f"{GREEN}{v:.4f}{RESET}" if k == "rate" else f"{v:.4f}"
                    print(f"  {k}: {val}")
                else:
                    print(f"  {k}: {v}")
    except Exception as e:
        print(f"Error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
