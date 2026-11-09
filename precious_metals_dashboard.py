#!/usr/bin/env python3
"""
Precious Metals Dashboard
=========================
A colorful dashboard that displays:
- Gold price (COMEX) converted to INR per 10g
- Silver price (COMEX) converted to INR per kg
- USD/INR exchange rate

Uses data from comexlive.org and moneycontrol.com
"""

from __future__ import annotations

import sys
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.columns import Columns
    from rich import box
except ImportError:
    print("Error: Rich library not installed. Install it with: pip install rich")
    sys.exit(1)

# Import converters
try:
    from gold_price_converter import convert_gold_price_usd_oz_to_inr_10g, add_duty_and_gst as gold_duty_gst
    from silver_price_converter import convert_silver_price_usd_oz_to_inr_kg, add_duty_and_gst as silver_duty_gst
    from get_gold_silver_comexlive import get_gold_silver
    from get_usdinr_moneycontrol import get_usdinr
except ImportError as e:
    print(f"Error: Missing required module. Ensure all modules are in the same folder.\n{e}")
    sys.exit(1)

# Constants
IMPORT_DUTY = 0.06  # 6%
GST = 0.03          # 3%

console = Console()


def create_header() -> Panel:
    """Create a colorful header for the dashboard."""
    title = Text()
    title.append("💰 ", style="yellow")
    title.append("PRECIOUS METALS DASHBOARD", style="bold magenta")
    title.append(" 💰", style="yellow")
    
    subtitle = Text()
    subtitle.append(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
    
    content = Text.assemble(title, "\n", subtitle)
    return Panel(content, border_style="cyan", box=box.DOUBLE)


def create_usdinr_panel(usdinr) -> Panel:
    """Create a panel showing USD/INR exchange rate."""
    content = Text()
    content.append("USD/INR: ", style="bold white")
    content.append(f"₹{usdinr.rate:.4f}", style="bold green")
    
    if usdinr.change is not None:
        change_style = "green" if usdinr.change >= 0 else "red"
        content.append(f"\nChange: ", style="dim")
        content.append(f"{usdinr.change:+.4f}", style=change_style)
        if usdinr.change_pct is not None:
            content.append(f" ({usdinr.change_pct:+.2f}%)", style=change_style)
    
    if usdinr.bid is not None and usdinr.ask is not None:
        content.append(f"\nBid/Ask: ", style="dim")
        content.append(f"{usdinr.bid:.4f} / {usdinr.ask:.4f}", style="cyan")
    
    if usdinr.high is not None and usdinr.low is not None:
        content.append(f"\nHigh/Low: ", style="dim")
        content.append(f"{usdinr.high:.4f} / {usdinr.low:.4f}", style="yellow")
    
    return Panel(content, title="[bold blue]💵 Exchange Rate[/bold blue]", border_style="blue", box=box.ROUNDED)


def create_gold_table(gold, rate) -> Table:
    """Create a table showing gold prices."""
    table = Table(title="🥇 [bold yellow]GOLD PRICES[/bold yellow]", box=box.ROUNDED, border_style="yellow")
    
    table.add_column("Metric", style="cyan", justify="left")
    table.add_column("USD/oz", style="white", justify="right")
    table.add_column("INR/10g", style="green", justify="right")
    table.add_column("After Tax*", style="bold green", justify="right")
    
    # Last price
    last_usd = gold.last
    last_inr = convert_gold_price_usd_oz_to_inr_10g(last_usd, rate, use_troy=True)
    last_final = gold_duty_gst(last_inr)
    table.add_row("Last", f"${last_usd:,.2f}", f"₹{last_inr:,.2f}", f"₹{last_final:,.2f}")
    
    # Close price
    close_usd = gold.close if gold.close else gold.last
    close_inr = convert_gold_price_usd_oz_to_inr_10g(close_usd, rate, use_troy=True)
    close_final = gold_duty_gst(close_inr)
    table.add_row("Close", f"${close_usd:,.2f}", f"₹{close_inr:,.2f}", f"₹{close_final:,.2f}")
    
    # High price
    if gold.high:
        high_inr = convert_gold_price_usd_oz_to_inr_10g(gold.high, rate, use_troy=True)
        high_final = gold_duty_gst(high_inr)
        table.add_row("High", f"${gold.high:,.2f}", f"₹{high_inr:,.2f}", f"₹{high_final:,.2f}")
    
    # Low price
    if gold.low:
        low_inr = convert_gold_price_usd_oz_to_inr_10g(gold.low, rate, use_troy=True)
        low_final = gold_duty_gst(low_inr)
        table.add_row("Low", f"${gold.low:,.2f}", f"₹{low_inr:,.2f}", f"₹{low_final:,.2f}")
    
    return table


def create_silver_table(silver, rate) -> Table:
    """Create a table showing silver prices."""
    table = Table(title="🥈 [bold cyan]SILVER PRICES[/bold cyan]", box=box.ROUNDED, border_style="cyan")
    
    table.add_column("Metric", style="cyan", justify="left")
    table.add_column("USD/oz", style="white", justify="right")
    table.add_column("INR/kg", style="green", justify="right")
    table.add_column("After Tax*", style="bold green", justify="right")
    
    # Last price
    last_usd = silver.last
    last_inr = convert_silver_price_usd_oz_to_inr_kg(last_usd, rate, use_troy=True)
    last_final = silver_duty_gst(last_inr)
    table.add_row("Last", f"${last_usd:.3f}", f"₹{last_inr:,.2f}", f"₹{last_final:,.2f}")
    
    # Close price
    close_usd = silver.close if silver.close else silver.last
    close_inr = convert_silver_price_usd_oz_to_inr_kg(close_usd, rate, use_troy=True)
    close_final = silver_duty_gst(close_inr)
    table.add_row("Close", f"${close_usd:.3f}", f"₹{close_inr:,.2f}", f"₹{close_final:,.2f}")
    
    # High price
    if silver.high:
        high_inr = convert_silver_price_usd_oz_to_inr_kg(silver.high, rate, use_troy=True)
        high_final = silver_duty_gst(high_inr)
        table.add_row("High", f"${silver.high:.3f}", f"₹{high_inr:,.2f}", f"₹{high_final:,.2f}")
    
    # Low price
    if silver.low:
        low_inr = convert_silver_price_usd_oz_to_inr_kg(silver.low, rate, use_troy=True)
        low_final = silver_duty_gst(low_inr)
        table.add_row("Low", f"${silver.low:.3f}", f"₹{low_inr:,.2f}", f"₹{low_final:,.2f}")
    
    return table


def create_change_panel(gold, silver) -> Panel:
    """Create a panel showing price changes."""
    content = Text()
    
    # Gold change
    content.append("Gold: ", style="bold yellow")
    if gold.change is not None:
        change_style = "green" if gold.change >= 0 else "red"
        arrow = "▲" if gold.change >= 0 else "▼"
        content.append(f"{arrow} ", style=change_style)
        content.append(f"${gold.change:+.2f}", style=change_style)
        if gold.change_pct is not None:
            content.append(f" ({gold.change_pct:+.2f}%)", style=change_style)
    else:
        content.append("N/A", style="dim")
    
    content.append("\n")
    
    # Silver change
    content.append("Silver: ", style="bold cyan")
    if silver.change is not None:
        change_style = "green" if silver.change >= 0 else "red"
        arrow = "▲" if silver.change >= 0 else "▼"
        content.append(f"{arrow} ", style=change_style)
        content.append(f"${silver.change:+.3f}", style=change_style)
        if silver.change_pct is not None:
            content.append(f" ({silver.change_pct:+.2f}%)", style=change_style)
    else:
        content.append("N/A", style="dim")
    
    return Panel(content, title="[bold white]📊 Daily Change[/bold white]", border_style="magenta", box=box.ROUNDED)


def create_summary_table(gold, silver, rate) -> Table:
    """Create a summary table with key prices."""
    table = Table(title="📋 [bold white]PRICE SUMMARY[/bold white]", box=box.DOUBLE, border_style="green")
    
    table.add_column("Metal", style="bold", justify="center")
    table.add_column("Current Price", style="bold green", justify="center")
    table.add_column("Unit", style="dim", justify="center")
    
    # Gold final price
    gold_inr = convert_gold_price_usd_oz_to_inr_10g(gold.last, rate, use_troy=True)
    gold_final = gold_duty_gst(gold_inr)
    table.add_row("🥇 Gold", f"₹{gold_final:,.2f}", "per 10 grams")
    
    # Silver final price
    silver_inr = convert_silver_price_usd_oz_to_inr_kg(silver.last, rate, use_troy=True)
    silver_final = silver_duty_gst(silver_inr)
    table.add_row("🥈 Silver", f"₹{silver_final:,.2f}", "per kg")
    
    return table


def create_footer() -> Panel:
    """Create a footer with additional info."""
    content = Text()
    content.append("* After Tax = Import Duty (6%) + GST (3%)\n", style="dim")
    content.append("Sources: ", style="dim")
    content.append("comexlive.org", style="blue underline")
    content.append(" | ", style="dim")
    content.append("moneycontrol.com", style="blue underline")
    
    return Panel(content, border_style="dim", box=box.SIMPLE)


def main() -> None:
    """Main function to display the precious metals dashboard."""
    console.clear()
    
    # Header
    console.print(create_header())
    console.print()
    
    # Fetch data with status
    with console.status("[bold green]Fetching live data...[/bold green]", spinner="dots"):
        try:
            console.log("[cyan]Fetching USD/INR from Moneycontrol...[/cyan]")
            usdinr = get_usdinr()
            
            console.log("[yellow]Fetching Gold & Silver from COMEX...[/yellow]")
            gold, silver = get_gold_silver()
            
        except Exception as e:
            console.print(f"[bold red]Error fetching data:[/bold red] {e}")
            sys.exit(1)
    
    rate = usdinr.rate
    
    # Display USD/INR and Change panels side by side
    console.print(Columns([
        create_usdinr_panel(usdinr),
        create_change_panel(gold, silver)
    ], equal=True, expand=True))
    console.print()
    
    # Display Gold and Silver tables side by side
    console.print(Columns([
        create_gold_table(gold, rate),
        create_silver_table(silver, rate)
    ], equal=True, expand=True))
    console.print()
    
    # Summary table
    console.print(create_summary_table(gold, silver, rate))
    console.print()
    
    # Footer
    console.print(create_footer())
    
    # Last trade time info
    if gold.last_trade or silver.last_trade:
        console.print()
        console.print("[dim]Last Trade Times:[/dim]")
        if gold.last_trade:
            console.print(f"  [yellow]Gold:[/yellow] {gold.last_trade}")
        if silver.last_trade:
            console.print(f"  [cyan]Silver:[/cyan] {silver.last_trade}")


if __name__ == "__main__":
    main()
