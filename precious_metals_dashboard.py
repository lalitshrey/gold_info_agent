#!/usr/bin/env python3
"""
Precious Metals Dashboard
=========================
A colorful dashboard that displays:
- Gold price (COMEX) converted to INR per 10g
- Silver price (COMEX) converted to INR per kg
- Gold & Silver prices from Moneycontrol (INR)
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
    from get_gold_silver_comexlive import get_gold_silver as get_comexlive_gold_silver
    from get_usdinr_moneycontrol import get_usdinr
    from get_gold_silver_moneycontrol import get_gold_silver as get_mc_gold_silver
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


def create_comex_gold_table(gold, rate) -> Table:
    """Create a table showing COMEX Gold prices."""
    table = Table(title="🥇 [bold yellow]COMEX GOLD (USD → INR)[/bold yellow]", box=box.ROUNDED, border_style="yellow")
    
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


def create_comex_silver_table(silver, rate) -> Table:
    """Create a table showing COMEX Silver prices."""
    table = Table(title="🥈 [bold cyan]COMEX SILVER (USD → INR)[/bold cyan]", box=box.ROUNDED, border_style="cyan")
    
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


def create_moneycontrol_gold_panel(gold_mc) -> Panel:
    """Create a panel showing Moneycontrol Gold prices."""
    content = Text()
    content.append("💰 Gold (Moneycontrol)", style="bold yellow")
    content.append("\n\nCurrent: ", style="dim")
    content.append(f"₹{gold_mc.last:,.2f}", style="bold green")
    content.append(" / 10g", style="dim")
    
    # Price change
    if gold_mc.change is not None:
        change_style = "green" if gold_mc.change >= 0 else "red"
        arrow = "▲" if gold_mc.change >= 0 else "▼"
        content.append(f"\n\nChange: ", style="dim")
        content.append(f"{arrow} ₹{gold_mc.change:+.2f}", style=change_style)
        if gold_mc.change_pct is not None:
            content.append(f" ({gold_mc.change_pct:+.2f}%)", style=change_style)
    
    # High/Low
    if gold_mc.high is not None or gold_mc.low is not None:
        content.append(f"\n\nHigh/Low: ", style="dim")
        if gold_mc.high:
            content.append(f"₹{gold_mc.high:,.2f}", style="green")
        if gold_mc.high and gold_mc.low:
            content.append(" / ", style="dim")
        if gold_mc.low:
            content.append(f"₹{gold_mc.low:,.2f}", style="red")
    
    # Open/Prev Close
    if gold_mc.open_ is not None or gold_mc.prev_close is not None:
        content.append(f"\n\nOpen/Prev: ", style="dim")
        if gold_mc.open_:
            content.append(f"₹{gold_mc.open_:,.2f}", style="cyan")
        if gold_mc.open_ and gold_mc.prev_close:
            content.append(" / ", style="dim")
        if gold_mc.prev_close:
            content.append(f"₹{gold_mc.prev_close:,.2f}", style="cyan")
    
    return Panel(content, title="[bold yellow]🏪 Moneycontrol Gold[/bold yellow]", border_style="yellow", box=box.ROUNDED)


def create_moneycontrol_silver_panel(silver_mc) -> Panel:
    """Create a panel showing Moneycontrol Silver prices."""
    content = Text()
    content.append("🥈 Silver (Moneycontrol)", style="bold cyan")
    content.append("\n\nCurrent: ", style="dim")
    content.append(f"₹{silver_mc.last:,.2f}", style="bold green")
    content.append(" / kg", style="dim")
    
    # Price change
    if silver_mc.change is not None:
        change_style = "green" if silver_mc.change >= 0 else "red"
        arrow = "▲" if silver_mc.change >= 0 else "▼"
        content.append(f"\n\nChange: ", style="dim")
        content.append(f"{arrow} ₹{silver_mc.change:+.2f}", style=change_style)
        if silver_mc.change_pct is not None:
            content.append(f" ({silver_mc.change_pct:+.2f}%)", style=change_style)
    
    # High/Low
    if silver_mc.high is not None or silver_mc.low is not None:
        content.append(f"\n\nHigh/Low: ", style="dim")
        if silver_mc.high:
            content.append(f"₹{silver_mc.high:,.2f}", style="green")
        if silver_mc.high and silver_mc.low:
            content.append(" / ", style="dim")
        if silver_mc.low:
            content.append(f"₹{silver_mc.low:,.2f}", style="red")
    
    # Open/Prev Close
    if silver_mc.open_ is not None or silver_mc.prev_close is not None:
        content.append(f"\n\nOpen/Prev: ", style="dim")
        if silver_mc.open_:
            content.append(f"₹{silver_mc.open_:,.2f}", style="cyan")
        if silver_mc.open_ and silver_mc.prev_close:
            content.append(" / ", style="dim")
        if silver_mc.prev_close:
            content.append(f"₹{silver_mc.prev_close:,.2f}", style="cyan")
    
    return Panel(content, title="[bold cyan]🏪 Moneycontrol Silver[/bold cyan]", border_style="cyan", box=box.ROUNDED)


def create_comex_change_panel(gold, silver) -> Panel:
    """Create a panel showing COMEX price changes."""
    content = Text()
    
    # Gold change
    content.append("Gold (COMEX): ", style="bold yellow")
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
    content.append("Silver (COMEX): ", style="bold cyan")
    if silver.change is not None:
        change_style = "green" if silver.change >= 0 else "red"
        arrow = "▲" if silver.change >= 0 else "▼"
        content.append(f"{arrow} ", style=change_style)
        content.append(f"${silver.change:+.3f}", style=change_style)
        if silver.change_pct is not None:
            content.append(f" ({silver.change_pct:+.2f}%)", style=change_style)
    else:
        content.append("N/A", style="dim")
    
    return Panel(content, title="[bold white]📊 COMEX Daily Change[/bold white]", border_style="magenta", box=box.ROUNDED)


def create_comparison_table(gold_comex, gold_mc, silver_comex, silver_mc, rate) -> Table:
    """Create a comparison table between COMEX and Moneycontrol prices."""
    table = Table(title="📋 [bold white]PRICE COMPARISON[/bold white]", box=box.DOUBLE, border_style="green")
    
    table.add_column("Metal", style="bold", justify="center")
    table.add_column("COMEX", style="bold yellow", justify="center")
    table.add_column("Moneycontrol", style="bold cyan", justify="center")
    table.add_column("Difference", style="bold", justify="center")
    
    # Gold comparison
    gold_comex_inr = convert_gold_price_usd_oz_to_inr_10g(gold_comex.last, rate, use_troy=True)
    gold_comex_final = gold_duty_gst(gold_comex_inr)
    
    if gold_mc:
        diff = gold_mc.last - gold_comex_final
        diff_pct = (diff / gold_comex_final) * 100 if gold_comex_final else 0
        diff_style = "green" if diff >= 0 else "red"
        diff_prefix = "+" if diff >= 0 else ""
        table.add_row(
            "🥇 Gold",
            f"₹{gold_comex_final:,.2f}",
            f"₹{gold_mc.last:,.2f}",
            f"[{diff_style}]{diff_prefix}₹{diff:,.2f} ({diff_pct:+.1f}%)[/]"
        )
    else:
        table.add_row("🥇 Gold", f"₹{gold_comex_final:,.2f}", "N/A", "N/A")
    
    # Silver comparison
    silver_comex_inr = convert_silver_price_usd_oz_to_inr_kg(silver_comex.last, rate, use_troy=True)
    silver_comex_final = silver_duty_gst(silver_comex_inr)
    
    if silver_mc:
        diff = silver_mc.last - silver_comex_final
        diff_pct = (diff / silver_comex_final) * 100 if silver_comex_final else 0
        diff_style = "green" if diff >= 0 else "red"
        diff_prefix = "+" if diff >= 0 else ""
        table.add_row(
            "🥈 Silver",
            f"₹{silver_comex_final:,.2f}",
            f"₹{silver_mc.last:,.2f}",
            f"[{diff_style}]{diff_prefix}₹{diff:,.2f} ({diff_pct:+.1f}%)[/]"
        )
    else:
        table.add_row("🥈 Silver", f"₹{silver_comex_final:,.2f}", "N/A", "N/A")
    
    return table


def create_summary_table(gold_comex, silver_comex, gold_mc, silver_mc, rate) -> Table:
    """Create a summary table with key prices from both sources."""
    table = Table(title="📋 [bold white]PRICE SUMMARY[/bold white]", box=box.DOUBLE, border_style="green")
    
    table.add_column("Metal", style="bold", justify="center")
    table.add_column("COMEX (After Tax)", style="bold yellow", justify="center")
    table.add_column("Moneycontrol", style="bold cyan", justify="center")
    table.add_column("Unit", style="dim", justify="center")
    
    # COMEX Gold final price
    gold_comex_inr = convert_gold_price_usd_oz_to_inr_10g(gold_comex.last, rate, use_troy=True)
    gold_comex_final = gold_duty_gst(gold_comex_inr)
    mc_gold = f"₹{gold_mc.last:,.2f}" if gold_mc else "N/A"
    table.add_row("🥇 Gold", f"₹{gold_comex_final:,.2f}", mc_gold, "per 10 grams")
    
    # COMEX Silver final price
    silver_comex_inr = convert_silver_price_usd_oz_to_inr_kg(silver_comex.last, rate, use_troy=True)
    silver_comex_final = silver_duty_gst(silver_comex_inr)
    mc_silver = f"₹{silver_mc.last:,.2f}" if silver_mc else "N/A"
    table.add_row("🥈 Silver", f"₹{silver_comex_final:,.2f}", mc_silver, "per kg")
    
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
            gold_comex, silver_comex = get_comexlive_gold_silver()
            
            console.log("[cyan]Fetching Gold & Silver from Moneycontrol...[/cyan]")
            try:
                gold_mc, silver_mc = get_mc_gold_silver()
            except Exception as e:
                console.log(f"[yellow]Could not fetch Moneycontrol prices: {e}[/yellow]")
                gold_mc, silver_mc = None, None
            
        except Exception as e:
            console.print(f"[bold red]Error fetching data:[/bold red] {e}")
            sys.exit(1)
    
    rate = usdinr.rate
    
    # Display USD/INR and COMEX Change panels side by side
    console.print(Columns([
        create_usdinr_panel(usdinr),
        create_comex_change_panel(gold_comex, silver_comex)
    ], equal=True, expand=True))
    console.print()
    
    # Display COMEX Gold and Silver tables side by side
    console.print(Columns([
        create_comex_gold_table(gold_comex, rate),
        create_comex_silver_table(silver_comex, rate)
    ], equal=True, expand=True))
    console.print()
    
    # Display Moneycontrol Gold and Silver panels side by side
    if gold_mc or silver_mc:
        mc_panels = []
        if gold_mc:
            mc_panels.append(create_moneycontrol_gold_panel(gold_mc))
        if silver_mc:
            mc_panels.append(create_moneycontrol_silver_panel(silver_mc))
        
        if mc_panels:
            console.print(Columns(mc_panels, equal=True, expand=True))
            console.print()
    
    # Display comparison table
    if gold_mc or silver_mc:
        console.print(create_comparison_table(gold_comex, gold_mc, silver_comex, silver_mc, rate))
        console.print()
    
    # Display summary table
    console.print(create_summary_table(gold_comex, silver_comex, gold_mc, silver_mc, rate))
    console.print()
    
    # Footer
    console.print(create_footer())
    
    # Last trade time info
    if gold_comex.last_trade or silver_comex.last_trade:
        console.print()
        console.print("[dim]COMEX Last Trade Times:[/dim]")
        if gold_comex.last_trade:
            console.print(f"  [yellow]Gold:[/yellow] {gold_comex.last_trade}")
        if silver_comex.last_trade:
            console.print(f"  [cyan]Silver:[/cyan] {silver_comex.last_trade}")


if __name__ == "__main__":
    main()

