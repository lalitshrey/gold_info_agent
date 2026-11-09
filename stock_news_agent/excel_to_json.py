from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pandas as pd


def read_excel_to_symbols(excel_path: Path) -> List[Dict[str, str]]:
    """Read Excel file and extract symbols from column D and names from column B."""
    try:
        # Read the Excel file
        df = pd.read_excel(excel_path)
        
        symbols = []
        for _, row in df.iterrows():
            symbol = str(row.iloc[3]).strip() if len(row) > 3 else ""  # Column D (index 3)
            name = str(row.iloc[1]).strip() if len(row) > 1 else ""    # Column B (index 1)
            
            # Skip empty rows
            if symbol and symbol != "nan" and name and name != "nan":
                symbols.append({
                    "symbol": symbol,
                    "name": name
                })
        
        return symbols
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return []


def write_symbols_json(symbols: List[Dict[str, str]], out_path: Path) -> None:
    """Write symbols to JSON file."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(symbols, f, ensure_ascii=False, indent=2)


def main() -> None:
    base_dir = Path(__file__).parent
    excel_file = base_dir / "Top_Nifty_500_2023.xlsx"
    out_file = base_dir / "static" / "nse_symbols.json"
    
    if not excel_file.exists():
        print(f"Excel file not found: {excel_file}")
        return
    
    symbols = read_excel_to_symbols(excel_file)
    write_symbols_json(symbols, out_file)
    print(f"Wrote {len(symbols)} symbols to {out_file}")


if __name__ == "__main__":
    main()
