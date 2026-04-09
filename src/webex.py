import logging
from datetime import datetime, timedelta
from wxc_sdk import WebexSimpleApi
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn, TimeElapsedColumn

logger = logging.getLogger("reconciliation")


def get_12_hour_windows(start_dt: datetime, end_dt: datetime):
    """Chunks any date range into 12-hour segments for Webex compliance."""
    windows = []
    current_start = start_dt
    while current_start < end_dt:
        current_end = current_start + timedelta(hours=12)
        if current_end > end_dt:
            current_end = end_dt
        windows.append((current_start, current_end))
        current_start = current_end
    return windows

def sync_webex_data(start_dt: datetime, end_dt: datetime, console, conn):
    """The core engine that performs the sync."""
    cursor = conn.cursor()
    api = WebexSimpleApi(retry_429=True)
    windows = get_12_hour_windows(start_dt, end_dt)

    logger.info(f"Starting Webex Sync: {len(windows)} windows to process.")

    # We pass the 'console' from cli.py to ensure Progress bars use the same Rich instance
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False
    ) as progress:
        
        overall_task = progress.add_task("[yellow]Windows Syncing", total=len(windows))
        record_task = progress.add_task("[cyan]Recordings Stored", total=None)

        for s_win, e_win in windows:
            s_iso = s_win.strftime('%Y-%m-%dT%H:%M:%SZ')
            e_iso = e_win.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            progress.update(overall_task, description=f"[yellow]Window: {s_win.strftime('%m/%d %H:%M')}")
            
            try:
                recordings_gen = api.converged_recordings.list_for_admin_or_compliance_officer(
                    from_=s_iso, to_=e_iso
                )

                batch = []
                window_count = 0
                
                for rec in recordings_gen:
                    session_id = rec.service_data.call_session_id if rec.service_data else None
                    
                    if session_id:
                        # Safety extraction for status
                        status_str = str(rec.status.value) if hasattr(rec.status, 'value') else str(rec.status)
                        
                        batch.append((
                            session_id,
                            rec.time_recorded,
                            rec.owner_email,
                            rec.duration_seconds,
                            status_str,
                            rec.model_dump_json()
                        ))
                    
                    window_count += 1
                    progress.advance(record_task)

                    if len(batch) >= 500:
                        cursor.executemany("INSERT OR IGNORE INTO webex_recordings VALUES (?,?,?,?,?,?)", batch)
                        conn.commit()
                        logger.info(f"Batched 500 records into DB (Window: {s_iso})")
                        batch = []

                if batch:
                    cursor.executemany("INSERT OR IGNORE INTO webex_recordings VALUES (?,?,?,?,?,?)", batch)
                
                # Mark history as success
                cursor.execute("INSERT OR REPLACE INTO sync_history VALUES (?,?,?,?,?)", 
                             (s_iso, e_iso, "SUCCESS", window_count, datetime.now().isoformat()))
                conn.commit()
                logger.debug(f"Window Completed: {s_iso} - Found {window_count} records.")
                
            except Exception as e:
                logger.error(f"Error in window {s_iso}: {e}")
                cursor.execute("INSERT OR REPLACE INTO sync_history VALUES (?,?,?,?,?)", 
                             (s_iso, e_iso, "FAILED", 0, datetime.now().isoformat()))
                conn.commit()

            progress.advance(overall_task)

    final_count = progress.tasks[1].completed
    logger.info(f"Webex Sync Finished. Total records indexed: {final_count}")
    return progress.tasks[1].completed