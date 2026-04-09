import os
import requests

from datetime import datetime, timedelta



def test_data_pull():
    base_url = os.getenv("CALABRIO_API_URL")
    user_id = os.getenv("CALABRIO_USER_ID")
    password = os.getenv("CALABRIO_PASSWORD")

    # 1. Authenticate (POST /authorize)
    auth_url = f"{base_url}/api/rest/authorize"
    auth_payload = {"userId": user_id, "password": password, "language": "en"}
    
    print("🔐 Authenticating...")
    auth_resp = requests.post(auth_url, json=auth_payload)
    auth_resp.raise_for_status()
    session_id = auth_resp.json().get("sessionId")
    print(f"✅ Session established: {session_id[:10]}...")

    # 2. Setup Headers (Cookie: hazelcast.sessionId)
    # Page 93 notes that this cookie is required for the Contact API
    headers = {
        "Cookie": f"hazelcast.sessionId={session_id}",
        "Accept": "application/json"
    }

    # 3. Define a small search window (e.g., the last 24 hours)
    # Contact API parameters from Page 94
    now = datetime.now()
    yesterday = now - timedelta(days=1)

    params = {
        "beginDate": yesterday.strftime('%Y-%m-%d'),
        "beginTime": "00:00",
        "endDate": now.strftime('%Y-%m-%d'),
        "endTime": "23:59",
        "limit": 5  # Small limit just for testing
    }

    # 4. Request Contact Metadata (GET /api/rest/recording/contact)
    contact_url = f"{base_url}/api/rest/recording/contact"
    print(f"📡 Fetching test records from: {contact_url}")
    
    try:
        data_resp = requests.get(contact_url, headers=headers, params=params)
        data_resp.raise_for_status()
        recordings = data_resp.json()

        if not recordings:
            print("⚠️ Success, but no recordings found in that 24h window.")
        else:
            print(f"🎉 Successfully retrieved {len(recordings)} records!")
            
            # Print the first record so we can find the ID field
            first_rec = recordings[0]
            print("\n--- Inspecting First Record ---")
            print(f"Start Time: {first_rec.get('startTime')}")
            print(f"Agent: {first_rec.get('agentEmail')}")
            
            # These are the candidates for your Webex CallSessionID
            print(f"icmCallId: {first_rec.get('icmCallId')}")
            print(f"assocCallId: {first_rec.get('assocCallId')}")
            print(f"externalId: {first_rec.get('externalId')}")

    except Exception as e:
        print(f"❌ Data pull failed: {e}")

if __name__ == "__main__":
    test_data_pull()