import requests
import csv
import json
from io import StringIO

NSE_CSV_URL = "https://www.nseindia.com/market-data/securities-available-for-trading"  
# Actually, NSE provides .csv links (check on that page for exact URL).  

def download_nse_csv():
    # Note: NSE often blocks non-browser user agents; might need headers + session
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
    }
    session = requests.Session()
    # first get page to pick actual CSV link
    r = session.get(NSE_CSV_URL, headers=headers)
    # parse r.text to find link to “Securities available for Equity segment (.csv)"
    # For simplicity, assume URL known; else you can search in HTML for .csv link

    # Example known CSV link (this may change over time)
    csv_url = "https://www.nseindia.com/content/equities/EQUITY_L.csv"
    resp = session.get(csv_url, headers=headers)
    resp.raise_for_status()
    return resp.text

def parse_csv_to_json(csv_text: str):
    reader = csv.DictReader(StringIO(csv_text))
    arr = []
    for row in reader:
        # pick relevant fields
        obj = {
            "symbol": row.get("SYMBOL") or row.get("Symbol"),
            "company_name": row.get("NAME OF COMPANY") or row.get("Company Name"),
            # include any other columns you want
        }
        arr.append(obj)
    return arr

def main():
    csv_text = download_nse_csv()
    data = parse_csv_to_json(csv_text)
    # write JSON
    with open("nse_listed_stocks.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Wrote", len(data), "stocks")

if __name__ == "__main__":
    main()
