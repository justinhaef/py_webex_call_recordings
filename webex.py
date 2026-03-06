import os
import sqlite3
import logging
from datetime import datetime, timedelta

# Webex SDK
from wxc_sdk import WebexSimpleApi

# UI and Logging
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    Progress, 
    SpinnerColumn, 
    TextColumn, 
    BarColumn, 
    MofNCompleteColumn, 
    TimeElapsedColumn
)

# 1. Logging Configuration
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True), logging.FileHandler("sync.log")]
)
logger = logging.getLogger("webex_sync")
console = Console()

# 2. Database Setup
def init_db(db_path="recordings.db"):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")
    
    # Recording Headers Table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS webex_recordings (
            call_session_id TEXT PRIMARY KEY,
            start_time TEXT,
            owner_email TEXT,
            duration_seconds INTEGER,
            status TEXT,
            raw_json TEXT
        )
    """)
    
    # Sync History Table (The Brain)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_history (
            window_start TEXT PRIMARY KEY,
            window_end TEXT,
            status TEXT,
            record_count INTEGER,
            last_run TEXT
        )
    """)
    conn.commit()
    return conn

# 3. Time Window Generator
def get_12_hour_windows(days=7):
    """Generates 12-hour blocks starting from 'days' ago up to now."""
    now = datetime.now().replace(microsecond=0)
    start_point = now - timedelta(days=days)
    
    windows = []
    current_start = start_point
    while current_start < now:
        current_end = current_start + timedelta(hours=12)
        if current_end > now:
            current_end = now
        windows.append((current_start, current_end))
        current_start = current_end
    return windows

# 4. Main Sync Logic
def sync_recordings():
    api = WebexSimpleApi(retry_429=True)
    conn = init_db()
    
    windows = get_12_hour_windows(days=7)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        overall_task = progress.add_task("[yellow]Overall Progress", total=len(windows))
        record_task = progress.add_task("[cyan]Total Records Stored", total=None)

        for start, end in windows:
            s_iso = start.strftime('%Y-%m-%dT%H:%M:%SZ')
            e_iso = end.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            progress.update(overall_task, description=f"[yellow]Syncing {start.strftime('%m/%d %H:%M')}")
            logger.info(f"Checking window: {s_iso} to {e_iso}")

            try:
                # API Call
                recordings_gen = api.converged_recordings.list_for_admin_or_compliance_officer(
                    from_=s_iso, to_=e_iso
                )

                batch = []
                window_count = 0
                
                for rec in recordings_gen:
                    session_id = rec.service_data.call_session_id if rec.service_data else None
                    if session_id:
                        batch.append((
                            session_id,
                            rec.time_recorded,
                            rec.owner_email,
                            rec.duration_seconds,
                            rec.status.value if hasattr(rec.status, 'value') else rec.status,
                            rec.model_dump_json()
                        ))
                    
                    window_count += 1
                    progress.advance(record_task)

                    if len(batch) >= 500:
                        conn.executemany("INSERT OR IGNORE INTO webex_recordings VALUES (?,?,?,?,?,?)", batch)
                        conn.commit()
                        batch = []

                if batch:
                    conn.executemany("INSERT OR IGNORE INTO webex_recordings VALUES (?,?,?,?,?,?)", batch)
                
                # Update Sync History on Success
                conn.execute("""
                    INSERT OR REPLACE INTO sync_history VALUES (?, ?, ?, ?, ?)
                """, (s_iso, e_iso, "SUCCESS", window_count, datetime.now().isoformat()))
                conn.commit()
                
                logger.info(f"✅ Success: {window_count} records for this window.")

            except Exception as e:
                logger.error(f"❌ Failed window {s_iso}: {e}")
                conn.execute("""
                    INSERT OR REPLACE INTO sync_history VALUES (?, ?, ?, ?, ?)
                """, (s_iso, e_iso, "FAILED", 0, datetime.now().isoformat()))
                conn.commit()

            progress.advance(overall_task)

    conn.close()
    console.print(f"[bold green]Sync Finished. Check 'sync.log' for details.[/]")

if __name__ == "__main__":
    sync_recordings()