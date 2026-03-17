import sqlite3
import os
import logging
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn, TimeElapsedColumn
from rich.logging import RichHandler

from .calabrio_connector import CalabrioConnector

logger = logging.getLogger("reconciliation")

console = Console()

def init_db():
    """The Single Source of Truth for the database schema."""
    db_path = os.getenv("DB_PATH", "recordings_cache.db")
    
    with sqlite3.connect(db_path) as conn:
        # 1. Webex Source Table
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
        
        # 2. Calabrio Archive Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calabrio_recordings (
                external_id TEXT PRIMARY KEY,
                start_time TEXT,
                duration_seconds INTEGER,
                status TEXT,
                raw_json TEXT
            )
        """)

        # 3. Sync History Table
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

def sync_calabrio_data(start_dt, end_dt, db_path, console, conn):
    """Orchestrates the Calabrio pull and save with batching."""
    connector = CalabrioConnector()
    cursor = conn.cursor()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        transient=False,
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Fetching Calabrio Archive...", total=None)
        
        # 1. Fetch records from API
        # Note: get_recordings returns the already-mapped list of tuples
        recordings = connector.get_recordings(start_dt, end_dt)
        progress.update(task, total=len(recordings))

        batch = []
        batch_size = 500
        total_saved = 0

        # 2. Batch Insert Logic
        for rec in recordings:
            batch.append(rec)
            
            if len(batch) >= batch_size:
                cursor.executemany(
                    "INSERT OR IGNORE INTO calabrio_recordings VALUES (?, ?, ?, ?, ?)",
                    batch
                )
                conn.commit()
                total_saved += len(batch)
                logger.info(f"📥 Batched {len(batch)} Calabrio records into DB.")
                batch = []
            
            progress.advance(task)

        # 3. Final remainder commit
        if batch:
            cursor.executemany(
                "INSERT OR IGNORE INTO calabrio_recordings VALUES (?, ?, ?, ?, ?)",
                batch
            )
            conn.commit()
            total_saved += len(batch)

    logger.info(f"✨ Calabrio Sync Finished. Total records indexed: {total_saved}")
    console.print(f"[bold green]✔ Calabrio Sync Complete:[/] {total_saved} records processed.")


def setup_logging():
    # 1. Create a log directory if it doesn't exist
    log_file = "reconciliation.log"
    
    # 2. Setup the File Handler (Plain text for easy reading/searching)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  # Capture everything in the file
    file_handler.setFormatter(file_formatter)

    # 3. Setup the Rich Handler (Colorful and pretty for the terminal)
    rich_handler = RichHandler(rich_tracebacks=True, markup=True)
    rich_handler.setLevel(logging.WARNING)

    # 4. Apply both to the root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[rich_handler, file_handler]
    )

    return logging.getLogger("reconciliation")

# Initialize the logger
log = setup_logging()