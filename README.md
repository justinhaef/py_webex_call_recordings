## Webex Recording Sync Utility
This Python application automates the synchronization of Webex Calling recordings into a local SQLite database for reconciliation and reporting. It is designed to handle high volumes (30,000+ recordings per day) by breaking requests into 12-hour windows and utilizing batch database writes.

## 🚀 Quick Start with uv
This project uses uv, an extremely fast Python package manager. You don't need to manually create virtual environments or use pip install; uv handles it all automatically.

1. Install uv
If you don't have it yet, run the installer:

macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh

Windows: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

2. Configure Environment Variables
Create a file named .env in the root directory. This file is ignored by Git to keep your credentials safe.

```Bash
# .env
WEBEX_ACCESS_TOKEN="your_personal_access_token_here"
```
3. Run the Application
You don't need to activate a virtual environment. Just run:

```Bash
uv run python sync_recordings.py
```
uv will automatically create a hidden .venv, install wxc_sdk, rich, and python-dotenv, and execute your script.

### 🛠 Features
Automated Windowing: Automatically splits a 7-day range into 12-hour blocks to comply with Webex API limits.

Resilient Sync History: Tracks the status of every 12-hour window in the sync_history table. If a window fails, it's logged for easy retry.

Performance Optimized: Uses SQLite WAL Mode and batch executemany inserts to handle 30k+ records without locking.

Rich UI: Real-time progress bars and structured logging directly in your terminal.

### 📂 Project Structure
`sync_recordings.py`: The main execution script.

`recordings_cache.db`: The SQLite database containing your synced data.

`sync.log`: A detailed log of all API calls and errors.

`.env`: Your private secrets (do not commit!).

### 🔍 Viewing the Data
If you use VS Code, we recommend the SQLite extension (by alexcvzz).

Open the Command Palette (`Ctrl+Shift+P`).

Type `SQLite: Open Database`.

Select `recordings_cache.db`.

Use the **SQLITE EXPLORER** in the sidebar to browse your `webex_recordings` and `sync_history` tables.

### 📝 Troubleshooting
Rate Limits: The script is configured to use `retry_429=True`. If you see the progress bar "pause," it is likely waiting for the Webex rate-limit bucket to refill.

Token Expiry: If you get a `401 Unauthorized error`, check that your `WEBEX_ACCESS_TOKEN` in `.env` hasn't expired.