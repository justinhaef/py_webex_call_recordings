## Webex Recording Sync Utility
This Python application automates the synchronization of Webex Calling recordings into a local SQLite database for reconciliation and reporting. It is designed to handle high volumes (30,000+ recordings per day) by breaking requests into 12-hour windows and utilizing batch database writes.

## 🚀 Quick Start with uv
This project uses `uv`, an extremely fast Python package manager. You don't need to manually create virtual environments or use pip install; uv handles it all automatically.

1. Install `uv`
If you don't have it yet, run the installer:

* **macOS/Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`

* **Windows**: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

## 🔑 How to get your Token:
**Check your Permissions:** Ensure your Webex account has the Full Admin or Compliance Officer role. Standard user accounts cannot pull recording metadata for an entire organization.

**Visit the Developer Portal:** Go to developer.webex.com.

**Log In:** Click Log In at the top right.

**Copy your Token:** Under the "Accounts and Authentication" section (or the "Documentation" getting started page), you will see a temporary Personal Access Token.

> * Note: These tokens are valid for 12 hours. For long-term automation, you should eventually create a "Service App" or "Integration" in the My Webex Apps section.

## 📝 Set up the .env file:
Create a file named .env in your project root and paste your token:

2. Configure Environment Variables
Create a file named `.env` in the root directory. This file is ignored by Git to keep your credentials safe.

```Bash
# .env
WEBEX_ACCESS_TOKEN="your_personal_access_token_here"
```
3. Run the Application
You don't need to activate a virtual environment. Just run:

```Bash
uv run --env-file .env main.py
```
`uv` will automatically create a hidden `.venv`, install `wxc_sdk` and `rich`, and execute your script.

### 🛠 Features
Automated Windowing: Automatically splits a 7-day range into 12-hour blocks to comply with Webex API limits.

Resilient Sync History: Tracks the status of every 12-hour window in the `sync_history` table. If a window fails, it's logged for easy retry.

Performance Optimized: Uses SQLite **WAL Mode** and batch executemany inserts to handle 30k+ records without locking.

Rich UI: Real-time progress bars and structured logging directly in your terminal.

### 📂 Project Structure
`main.py`: The main execution script.

`webex.py`: Where all the work gets done!

`recordings.db`: The SQLite database containing your synced data.

`sync.log`: A detailed log of all API calls and errors.

`.env`: Your private secrets (do not commit!).

### 🔍 Viewing the Data
If you use VS Code, we recommend the SQLite extension (by alexcvzz).

Open the Command Palette (`Ctrl+Shift+P`).

Type `SQLite: Open Database`.

Select `recordings.db`.

Use the **SQLITE EXPLORER** in the sidebar to browse your `webex_recordings` and `sync_history` tables.

### 📝 Troubleshooting
Rate Limits: The script is configured to use `retry_429=True`. If you see the progress bar "pause," it is likely waiting for the Webex rate-limit bucket to refill.

Token Expiry: If you get a `401 Unauthorized error`, check that your `WEBEX_ACCESS_TOKEN` in `.env` hasn't expired.

### 🧪 Testing & Dry Runs
Before running a full 7-day sync, it is recommended to perform a "Dry Run" to verify your connection and database setup.

1. Test the Connection
You can limit the script to a single 12-hour window by modifying the days parameter in the main block of `webex.py`:

```Python
# Change this for testing:
windows = get_12_hour_windows(days=0.5) 
```
2. Verify the Database
After the test run, verify that the data landed correctly using the SQLite extension in VS Code:

Open the **SQLITE EXPLORER** in the sidebar.

Right-click `webex_recordings` and select **Show Table**.

Ensure the `status` and `call_session_id` columns are populated (not null).

### ⌨️ CLI Usage
This tool features a robust Command Line Interface (CLI) powered by `Typer` and `Rich`. By default, the script syncs data from the last 7 days, but you can override this for specific backfills.

#### Basic Commands
Sync the default range (Last 7 Days):
```Bash
uv run --env-file .env main.py
```
Sync a specific number of days:
```Bash
# Sync the last 48 hours
uv run --env-file .env main.py --days 2
```
Sync a specific date range (Backfill):
If you provide a `--start` date, the `--days` flag is ignored.
```Bash
# Sync from March 1st to March 5th
uv run --env-file .env main.py --start 2026-03-01 --end 2026-03-05
```
*Note: If you provide `--start` but omit `--end`, the script will automatically sync from your start date up until now.*

### Command Options
| Flag | Shorthand | Description | Default |
| :--- | :--- | :--- | :--- |
| `--days` | `-d` | Number of days to look back from now. | `7.0` |
| `--start` | | Explicit start date in `YYYY-MM-DD` format. | `None` |
| `--end` | | Explicit end date in `YYYY-MM-DD` format. | `Now` |
| `--help` | | Show the help menu and exit. | |

### 🛠 Troubleshooting the CLI
* Date Format: Ensure dates are entered as Year-Month-Day (e.g., 2026-03-07).
* Validation: The script will prevent execution if the `--start` date is chronologically after the `--end` date.
* Help Menu: Run `uv run main.py --help` at any time to see the beautiful, color-coded documentation built into the tool.

## 🛡 Best Practices
**Token Lifespan**: Webex Personal Access Tokens typically last only 12 hours. If you are running a long-term sync, consider using a **Webex Integration (OAuth)** or a **Service App** for a permanent Refresh Token.

**Database Backups**: While SQLite is robust, it's good practice to copy the `recordings.db` file to a backup location before running a "Clear and Resync" operation.

**Rate Limits**: If the terminal shows multiple 429 Too Many Requests warnings, the script will automatically pause. Do not stop the script; it will resume as soon as the Webex API allows.