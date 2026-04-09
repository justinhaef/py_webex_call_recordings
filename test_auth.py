import os
import requests


def test_calabrio_auth():
    # Load your credentials
    base_url = os.getenv("CALABRIO_API_URL")  # e.g., https://tenant.calabriocloud.com
    user_id = os.getenv("CALABRIO_USER_ID")
    password = os.getenv("CALABRIO_PASSWORD")
 
    
    # Page 55: POST Protocol and URI
    auth_url = f"{base_url}/api/rest/authorize"
    
    # Page 43 & 55: Request Fields
    payload = {
        "userId": user_id,
        "password": password,
        "language": "en"
    }

    print(f"🚀 Attempting to authorize at: {auth_url}")
    
    try:
        response = requests.post(auth_url, json=payload)

        # Check for HTTP errors (like 401 Unauthorized)
        response.raise_for_status()
        
        # Page 56: Successful Response
        data = response.json()
        session_id = data.get("sessionId")
        
        if session_id:
            print("✅ Success! Authenticated with Calabrio.")
            print(f"🔑 Session ID: {session_id}")
            print(f"⏳ This session will expire in 2 hours of inactivity.") # [cite: 67, 348, 486]
        else:
            print("⚠️ Response received, but no sessionId found.")
            print(f"Full Response: {data}")

    except requests.exceptions.HTTPError as err:
        print(f"❌ HTTP Error: {err}")
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    test_calabrio_auth()