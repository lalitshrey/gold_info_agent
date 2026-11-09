"""
Silver Price Converter
Fetches COMEX Silver (last, close) from comexlive.org and USD/INR from Moneycontrol,
then converts silver price from USD per troy ounce to INR per kg.

Outputs: Last, Close (both in INR per kg).
Final price after Import Duty (6%) + GST (3%).
"""

from __future__ import annotations

# 1 troy ounce = 31.1034768 grams (COMEX uses troy)
GRAMS_PER_TROY_OZ = 31.1035
IMPORT_DUTY = 0.06   # 6%
GST = 0.03           # 3% (on duty-inclusive value)
GREEN = "\033[32m"
RESET = "\033[0m"


def add_duty_and_gst(price_inr: float) -> float:
    """Apply Import Duty (6%) then GST (3%) on duty-inclusive value. Returns final price."""
    after_duty = price_inr * (1 + IMPORT_DUTY)
    return after_duty * (1 + GST)


def convert_silver_price_usd_oz_to_inr_kg(
    price_usd_per_oz: float,
    usd_to_inr_rate: float,
    *,
    use_troy: bool = True,
) -> float:
    """
    Convert silver price from USD per ounce to INR per kg.

    Args:
        price_usd_per_oz: Price in USD per (troy) ounce
        usd_to_inr_rate: USD to INR exchange rate
        use_troy: If True, use troy ounce (31.1035 g). If False, use avoirdupois (28.3495 g).

    Returns:
        Price in INR per kg
    """
    grams_per_oz = GRAMS_PER_TROY_OZ if use_troy else 28.3495
    ounces_per_kg = 1000 / grams_per_oz
    price_inr_per_oz = price_usd_per_oz * usd_to_inr_rate
    return price_inr_per_oz * ounces_per_kg


def main() -> None:
    """Fetch silver (comexlive) + USD/INR (moneycontrol), convert and print Last & Close."""
    print("=" * 50)
    print("Silver Price Converter: COMEX USD/oz → INR/kg")
    print("=" * 50)

    try:
        from get_gold_silver_comexlive import get_gold_silver
        from get_usdinr_moneycontrol import get_usdinr
    except ImportError as e:
        print(f"Error: Missing module. Install dependencies and ensure get_gold_silver_comexlive and get_usdinr_moneycontrol are in the same folder.\n{e}")
        raise SystemExit(1) from e

    print("Fetching COMEX Silver (comexlive.org)...")
    _, silver = get_gold_silver()
    print("Fetching USD/INR (Moneycontrol)...")
    usdinr = get_usdinr()
    rate = usdinr.rate

    last_usd = silver.last
    close_usd = silver.close
    if close_usd is None:
        close_usd = last_usd  # fallback if close missing

    last_inr = convert_silver_price_usd_oz_to_inr_kg(last_usd, rate, use_troy=True)
    close_inr = convert_silver_price_usd_oz_to_inr_kg(close_usd, rate, use_troy=True)
    last_final = add_duty_and_gst(last_inr)
    close_final = add_duty_and_gst(close_inr)

    print()
    print("=" * 50)
    print("Conversion Results (INR per kg)")
    print("=" * 50)
    print(f"COMEX Silver Last:  ${last_usd:,.2f}/oz  →  {GREEN}₹{last_inr:,.2f}{RESET} per kg")
    print(f"COMEX Silver Close: ${close_usd:,.2f}/oz  →  {GREEN}₹{close_inr:,.2f}{RESET} per kg")
    print()
    print("Output:")
    print(f"  Last:  ₹{last_inr:,.2f}")
    print(f"  Close: ₹{close_inr:,.2f}")
    print()
    print("Final price (after Import Duty 6% + GST 3%):")
    print(f"  {GREEN}Last:  ₹{last_final:,.2f}{RESET}")
    print(f"  {GREEN}Close: ₹{close_final:,.2f}{RESET}")
    if silver.change is not None:
        pct = f" ({silver.change_pct:+.2f}%)" if silver.change_pct is not None else ""
        print(f"  Silver change (COMEX): {silver.change:+.2f}{pct}")
    print(f"  USD/INR: {rate:.4f}")
    print("=" * 50)


if __name__ == "__main__":
    main()
