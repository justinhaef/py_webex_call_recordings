import typer
from typing import Optional
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel

# Import the engine from your logic file
from .webex import run_sync_logic

app = typer.Typer(rich_markup_mode="rich")
console = Console()

@app.command()
def sync(
    days: float = typer.Option(
        7.0, "--days", "-d", 
        help="Number of days to sync backwards from now."
    ),
    start: Optional[str] = typer.Option(
        None, "--start", 
        help="Explicit start date (YYYY-MM-DD). Overrides --days."
    ),
    end: Optional[str] = typer.Option(
        None, "--end", 
        help="Explicit end date (YYYY-MM-DD)."
    )
):
    """
    [bold cyan]Webex Recording Sync Tool[/bold cyan] 🚀
    
    Syncs recording metadata into SQLite using 12-hour windows.
    Default is the last 7 days.
    """
    
    # 1. Determine the Date Range
    try:
        if start:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            # If start is provided but no end, go up to 'now'
            end_dt = datetime.strptime(end, "%Y-%m-%d") if end else datetime.now()
        else:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=days)
            
        # 2. Validation Check
        if start_dt > end_dt:
            console.print("[bold red]Error:[/] Start date cannot be after the end date! 🛑")
            raise typer.Exit(code=1)

    except ValueError:
        console.print("[bold red]Error:[/] Invalid date format. Please use [yellow]YYYY-MM-DD[/].")
        raise typer.Exit(code=1)

    # 3. User Feedback
    console.print(Panel(
        f"📅 [bold]Sync Range:[/]\n"
        f"From: [green]{start_dt.strftime('%Y-%m-%d %H:%M')}[/]\n"
        f"To:   [green]{end_dt.strftime('%Y-%m-%d %H:%M')}[/]",
        expand=False,
        border_style="cyan"
    ))

    # 4. Trigger the Engine
    total_synced = run_sync_logic(start_dt, end_dt, console)
    
    console.print(f"\n[bold green]✔ Done![/] Processed [yellow]{total_synced}[/] recordings.")

if __name__ == "__main__":
    app()