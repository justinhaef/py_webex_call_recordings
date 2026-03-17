import sqlite3
import os
from datetime import datetime
from jinja2 import Template

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sync Reconciliation Report</title>
    <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <style>
        :root { --primary: #0070d2; --danger: #d32f2f; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f8f9fa; margin: 40px; }
        .dashboard-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
        .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 5px solid var(--primary); }
        .card.missing { border-top-color: var(--danger); }
        .card h3 { margin: 0; font-size: 0.9rem; color: #666; text-transform: uppercase; }
        .card .value { font-size: 2.5rem; font-weight: bold; margin-top: 10px; }
        .table-container { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    </style>
</head>
<body>
    <div class="dashboard-grid">
        <div class="card"><h3>Total Webex</h3><div class="value">{{ total }}</div></div>
        <div class="card"><h3>Success Rate</h3><div class="value">{{ percent }}%</div></div>
        <div class="card missing"><h3>Missing In Calabrio</h3><div class="value" style="color:var(--danger)">{{ missing_cnt }}</div></div>
    </div>
    <div class="table-container">
        <table id="reportTable" class="display">
            <thead>
                <tr><th>Webex Session ID</th><th>Date</th><th>User</th><th>Status</th></tr>
            </thead>
            <tbody>
                {% for row in missing_records %}
                <tr><td><code>{{ row[0] }}</code></td><td>{{ row[1] }}</td><td>{{ row[2] }}</td><td style="color:red">Missing</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script>$(document).ready(function() { $('#reportTable').DataTable({ pageLength: 25, order: [[1, 'desc']] }); });</script>
</body>
</html>
"""

def generate_html_report():
    db_path = os.getenv("DB_PATH", "recordings_cache.db")
    conn = sqlite3.connect(db_path)
    
    # 1. Get Summary Stats
    total_webex = conn.execute("SELECT COUNT(*) FROM webex_recordings").fetchone()[0]
    
    # 2. Find the Gaps (The SQL Magic)
    query = """
        SELECT w.call_session_id, w.start_time, w.owner_email
        FROM webex_recordings w
        LEFT JOIN calabrio_recordings c ON w.call_session_id = c.external_id
        WHERE c.external_id IS NULL;
    """
    missing = conn.execute(query).fetchall()
    missing_cnt = len(missing)
    percent = round(((total_webex - missing_cnt) / total_webex) * 100, 1) if total_webex > 0 else 0

    # 3. Render and Save
    template = Template(HTML_TEMPLATE)
    output = template.render(
        missing_records=missing,
        total=total_webex,
        missing_cnt=missing_cnt,
        percent=percent,
        date=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    
    with open("sync_report.html", "w") as f:
        f.write(output)
    conn.close()