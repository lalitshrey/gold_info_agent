from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import httpx


YAHOO_SCREENER_URL = "https://query2.finance.yahoo.com/v1/finance/screener"


def fetch_all_nse_symbols(page_size: int = 250) -> List[Dict[str, str]]:
    headers = {
        "User-Agent": "stock-news-agent/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    offset = 0
    results: List[Dict[str, str]] = []
    with httpx.Client(headers=headers, timeout=20) as client:
        while True:
            payload = {
                "offset": offset,
                "size": page_size,
                "sortField": "symbol",
                "sortType": "asc",
                "quoteType": "EQUITY",
                "query": {
                    "operator": "AND",
                    "operands": [
                        {"operator": "eq", "operands": ["region", "in"]},
                        {"operator": "eq", "operands": ["exchange", "NSE"]},
                    ],
                },
                "userId": "",
                "userIdType": "guid",
            }
            resp = client.post(YAHOO_SCREENER_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            quotes = (
                data.get("finance", {})
                .get("result", [{}])[0]
                .get("quotes", [])
            )
            if not quotes:
                break
            for q in quotes:
                raw_symbol = str(q.get("symbol", "")).strip()
                name = (
                    str(q.get("longName") or q.get("shortName") or raw_symbol).strip()
                )
                # Normalize: Yahoo NSE symbols usually end with .NS
                symbol = raw_symbol[:-3] if raw_symbol.endswith(".NS") else raw_symbol
                if symbol:
                    results.append({"symbol": symbol, "name": name})
            if len(quotes) < page_size:
                break
            offset += page_size
    # De-duplicate and sort
    seen = set()
    unique: List[Dict[str, str]] = []
    for item in results:
        key = item["symbol"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    unique.sort(key=lambda x: x["symbol"]) 
    return unique


def write_symbols_json(symbols: List[Dict[str, str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(symbols, f, ensure_ascii=False, indent=2)


def main() -> None:
    base_dir = Path(__file__).parent
    out_file = base_dir / "static" / "nse_symbols.json"
    symbols = fetch_all_nse_symbols()
    write_symbols_json(symbols, out_file)
    print(f"Wrote {len(symbols)} symbols to {out_file}")


if __name__ == "__main__":
    main()


