
import requests
import json
import logging
import os
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

USERNAME = os.environ.get("SI_USERNAME")
PASSWORD = os.environ.get("SI_PASSWORD")
API_KEY_RO = "s4GH8119xFyX"
AUTH_URL = "https://lambda.stratus.ai/auth/login"
SAPI_URL = "https://apipri.stratus.ai/sapi"

def get_token():
    if not USERNAME or not PASSWORD: return None
    try:
        r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
        return r.json().get("token")
    except: return None

def test_guessing():
    token = get_token()
    if not token: return
    
    # Extract User ID (842506)
    USER_ID = "842506"

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    # Ensure session exists (Submit Plan)
    requests.post("https://portal.stratus.ai/api/efb/submitFlightPlan", headers=headers, json={"callsign":"N123", "aircraft":"C172", "flight_rules":"VFR"}, timeout=5)
    time.sleep(1)

    combinations = [
        ("API_KEY=RO, FLIGHT_ID=None", {"api_key": API_KEY_RO}),
        ("API_KEY=Token, FLIGHT_ID=None", {"api_key": token}),
        ("API_KEY=RO, FLIGHT_ID=UserID", {"api_key": API_KEY_RO, "flight_id": USER_ID}),
        ("API_KEY=Token, FLIGHT_ID=UserID", {"api_key": token, "flight_id": USER_ID}),
        ("API_KEY=RO, X-Flight-ID=UserID", {"api_key": API_KEY_RO}, {"X-Flight-ID": USER_ID}),
        ("API_KEY=Token, X-Flight-ID=UserID", {"api_key": token}, {"X-Flight-ID": USER_ID}),
    ]
    
    for label, params, *extra_headers in combinations:
        h = headers.copy()
        if extra_headers: h.update(extra_headers[0])
        
        # Add common params
        p = params.copy()
        p.update({"gate": "PARKING 1", "airport": "KTRK"})
        
        try:
            r = requests.get(f"{SAPI_URL}/assignGate", params=p, headers=h, timeout=5)
            logger.info(f"[{label}] -> {r.status_code} {r.text}")
        except Exception as e: logger.error(e)

if __name__ == "__main__":
    test_guessing()
