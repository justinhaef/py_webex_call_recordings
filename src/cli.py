import os
import sqlite3
import typer
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel

# Importing from your specific file structure
from .logic import init_db, sync_calabrio_data
from .webex import sync_webex_data  # Your webex logic is in webex.py
from .reporter import generate_html_report

app = typer.Typer(help="Webex to Calabrio Recording Reconciliation Tool")
console = Console()

@app.command()
def sync(
    days: float = typer.Option(7.0, "--days", "-d", help="Number of days to sync"),
    start: str = typer.Option(None, "--start", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
    report: bool = typer.Option(True, "--report/--no-report", help="Generate HTML report after sync")
):
    """
    Performs a full reconciliation: 
    1. Pulls from Webex 
    2. Pulls from Calabrio 
    3. Generates HTML report
    """
 
    # 1. Handle Time Range Logic
    try:
        if start:
            start_dt = datetime.strptime(start, "%Y-%m-%d")
            # If start is provided but no end, go up to 'now'
            end_dt = datetime.strptime(end, "%Y-%m-%d") if end else datetime.now()
        else:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=days)
            
        # 1.1. Validation Check
        if start_dt > end_dt:
            console.print("[bold red]Error:[/] Start date cannot be after the end date! 🛑")
            raise typer.Exit(code=1)

    except ValueError:
        console.print("[bold red]Error:[/] Invalid date format. Please use [yellow]YYYY-MM-DD[/].")
        raise typer.Exit(code=1)

    # 1.2. User Feedback
    console.print(Panel(
        f" [bold]Sync Range:[/]\n"
        f"From: [green]{start_dt.strftime('%Y-%m-%d %H:%M')}[/]\n"
        f"To:   [green]{end_dt.strftime('%Y-%m-%d %H:%M')}[/]",
        expand=False,
        border_style="cyan"
    ))

    # 2. Ensure DB is ready
    init_db()
    db_path = os.getenv("DB_PATH", "recordings_cache.db")
    conn = sqlite3.connect(db_path)
    try:
        # 3. Step 1: Webex Sync (Source of Truth)
        console.print("[bold yellow]Step 1: Fetching Webex Recordings...[/]")
        sync_webex_data(start_dt, end_dt, console, conn)

        # 4. Step 2: Calabrio Sync (The Archive)
        console.print("\n[bold yellow]Step 2: Fetching Calabrio Recordings...[/]")
        # Passing 'recordings_cache.db' as the path used in init_db
        sync_calabrio_data(start_dt, end_dt, db_path, console, conn)

        # 5. Step 3: Reporting
        if report:
            console.print("\n[bold yellow]Step 3: Generating Reconciliation Report...[/]")
            report_path = generate_html_report(start_dt, end_dt)
            console.print(f"[bold green]✔ Success! Report generated:[/] [cyan]{report_path}[/]")

        console.print("\n[bold green]✨ All tasks complete.[/]\n")
    finally:
        conn.close()

if __name__ == "__main__":
    app()