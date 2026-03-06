import os
import sqlite3
from datetime import datetime, timedelta
# from dotenv import load_dotenv

# Webex SDK
from wxc_sdk import WebexSimpleApi

# Rich UI Components
from rich.console import Console
from rich.progress import (
    Progress, 
    SpinnerColumn, 
    TextColumn, 
    BarColumn, 
    MofNCompleteColumn, 
    TimeElapsedColumn
)
from rich.panel import Panel
from rich.table import Table

# Initialize Rich console
console = Console()

# 1. Configuration & Setup
# load_dotenv()
DB_PATH = "recordings.db"

def init_db():
    """Initializes SQLite with performance-oriented settings (WAL mode)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS webex_recordings (
            sessionId TEXT PRIMARY KEY,
            startTime TEXT,
            ownerEmail TEXT,
            raw_json TEXT
        )
    """)
    # Index for fast reconciliation later
    conn.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON webex_recordings(sessionId)")
    conn.commit()
    return conn

def fetch_and_store():
    # Setup Webex API (automatically uses WEBEX_ACCESS_TOKEN from .env)
    api = WebexSimpleApi(retry_429=True)
    conn = init_db()
    
    # 2026 Webex Rule: 12-hour windows only.
    # We'll set a window for 'Yesterday'
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)

    console.print(Panel(f"[bold blue]Webex Recording Sync[/]\n[dim]Window: {start_time.isoformat()} to {end_time.isoformat()}[/]"))

    # 2. The Main Sync Loop
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False
    ) as progress:
        
        sync_task = progress.add_task("[cyan]Downloading metadata...", total=None)
        
        # list_for_admin_or_compliance_officer returns a generator (auto-paginating)
        recordings_gen = api.converged_recordings.list_for_admin_or_compliance_officer(
            from_=start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            to_=end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        )

        batch = []
        batch_size = 500
        
        for rec in recordings_gen:
            # Shared ID for Calabrio matching
            session_id = rec.service_data.call_session_id if rec.service_data else None
            
            if session_id:
                # wxc_sdk models use model_dump_json() for clean serialization
                batch.append((
                    session_id, 
                    rec.time_recorded, 
                    rec.owner_email, 
                    rec.model_dump_json()
                ))
            
            progress.advance(sync_task)

            # Performance: Commit in blocks of 500
            if len(batch) >= batch_size:
                conn.executemany(
                    "INSERT OR IGNORE INTO webex_recordings VALUES (?, ?, ?, ?)", 
                    batch
                )
                conn.commit()
                batch = []
                progress.update(sync_task, description=f"[green]Stored {progress.tasks[0].completed} records...")

        # Final cleanup for remaining records
        if batch:
            conn.executemany("INSERT OR IGNORE INTO webex_recordings VALUES (?, ?, ?, ?)", batch)
            conn.commit()

    total = progress.tasks[0].completed
    console.print(f"\n[bold green]✔ Sync Complete![/] Total: [yellow]{total}[/] recordings stored.")
    conn.close()
    return total

if __name__ == "__main__":
    try:
        fetch_and_store()
    except Exception as e:
        console.print(f"[bold red]Critical Error:[/] {e}")