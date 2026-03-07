import typer
from typing import Optional
from datetime import datetime, timedelta
from .webex import run_sync_logic
from rich.console import Console

app = typer.Typer(rich_markup_mode="rich")
console = Console()

@app.command()
def sync(
    days: Optional[float] = typer.Option(
        7.0, "--days", "-d", help="Number of days to sync backwards from now."
    ),
    start: Optional[str] = typer.Option(
        None, "--start", help="Explicit start date (YYYY-MM-DD). Overrides --days."
    ),
    end: Optional[str] = typer.Option(
        None, "--end", help="Explicit end date (YYYY-MM-DD)."
    )
):
    """
    [bold cyan]Webex Recording Sync Tool[/bold cyan] 🚀
    
    Syncs recording metadata into SQLite using 12-hour windows.
    """
    
    # Logic to calculate the range
    if start:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d") if end else datetime.now()
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=days)

    # Call your existing sync function with these dates
    console.print(f"📅 Syncing from [green]{start_dt}[/] to [green]{end_dt}[/]")
    run_sync_logic(start_dt, end_dt, console)

if __name__ == "__main__":
    app()