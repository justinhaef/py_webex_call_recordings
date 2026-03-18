import os
import requests
import logging
from datetime import datetime
from rich.console import Console
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("reconciliation")

console = Console()

class CalabrioConnector:
    def __init__(self):
        self.base_url = os.getenv("CALABRIO_API_URL")
        self.user_id = os.getenv("CALABRIO_USER_ID")
        self.password = os.getenv("CALABRIO_PASSWORD")
        self.session_id = None

    def authenticate(self):
        """POST /authorize to obtain the required session ID"""
        url = f"{self.base_url}/api/rest/authorize"
        payload = {
            "userId": self.user_id, 
            "password": self.password, 
            "language": "en"
        }
        
        logger.info("[bold cyan] Authenticating with Calabrio...[/]")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        self.session_id = response.json().get("sessionId")
        logger.info(f"[bold green] Session Active:[/] {self.session_id[:10]}...")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _get_page(self, endpoint, params):
        if not self.session_id:
            self.authenticate()

        headers = {
            "Cookie": f"hazelcast.sessionId={self.session_id}",
            "Accept": "application/json"
        }
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        
        # If session timed out (401), re-authenticate and retry once
        if response.status_code == 401:
            self.authenticate()
            return self._get_page(endpoint, params)
            
        response.raise_for_status()
        return response.json()

    def get_recordings(self, start_dt, end_dt):
        """Fetches recordings from the Contact API with 100-record limit"""
        all_recs = []
        params = {
            "beginDate": start_dt.strftime('%Y-%m-%d'),
            "beginTime": start_dt.strftime('%H:%M'),
            "endDate": end_dt.strftime('%Y-%m-%d'),
            "endTime": end_dt.strftime('%H:%M'),
            "limit": 100
        }
        
        logger.info(f"Querying Calabrio: [yellow]{params['beginDate']}[/] to [yellow]{params['endDate']}[/]")
        
        data = self._get_page("api/rest/recording/contact", params)
        if isinstance(data, list):
            all_recs.extend(data)
            
        return self._map_to_db(all_recs)

    def _map_to_db(self, recordings):
        """Maps Calabrio fields to SQLite schema"""
        mapped = []
        for r in recordings:
            # assocCallId is the key field for matching Webex call_session_id
            ext_id = r.get("assocCallId") or r.get("icmCallId")
            if ext_id:
                mapped.append((
                    str(ext_id),
                    r.get("startTime"),
                    r.get("callDuration", 0) // 1000, # ms to seconds
                    "Archived" if r.get("audioUploaded") else "Pending",
                    str(r)
                ))
        return mapped