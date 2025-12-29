
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

def test_sapi_fuzz():
    token = get_token()
    if not token: return
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 1. Ensure Flight Plan Exists
    requests.post("https://portal.stratus.ai/api/efb/submitFlightPlan", headers=headers, json={"callsign":"N123", "aircraft":"C172", "flight_rules":"VFR"}, timeout=5)
    
    # Payload variations
    user_id = "842506"
    base_sim = {
        "variables": {"PLANE LATITUDE": 34.0, "PLANE LONGITUDE": -118.0, "TITLE": "Cessna 172"},
        "name": "StratusML", "version": "1.0"
    }
    
    variations = [
        ("Base + RO Key", {"sim": base_sim, "api_key": API_KEY_RO}),
        ("Base + Token", {"sim": base_sim, "api_key": token}),
        ("Base + UserID", {"sim": base_sim, "api_key": API_KEY_RO, "userid": user_id}),
        ("Base + Email", {"sim": base_sim, "api_key": API_KEY_RO, "email": USERNAME}),
        ("Sim with UserID", {"sim": {**base_sim, "userid": user_id}, "api_key": API_KEY_RO}),
        ("Sim with Email", {"sim": {**base_sim, "email": USERNAME}, "api_key": API_KEY_RO}),
    ]
    
    for label, payload in variations:
        logger.info(f"--- {label} ---")
        try:
            # Send Telemetry
            r = requests.post(f"{SAPI_URL}/v1/input", headers=headers, json=payload, timeout=5)
            logger.info(f"   Input: {r.status_code} {r.text}")
            
            time.sleep(1)
            
            # Check Session
            r = requests.get(f"{SAPI_URL}/assignGate", params={"api_key": API_KEY_RO, "gate": "PARKING 1", "airport": "KTRK"}, headers=headers, timeout=5)
            if "No active flight" not in r.text:
                logger.info(f"   SUCCESS! {r.text}")
            else:
                logger.info(f"   Fail: {r.text}")
                
        except Exception as e: logger.error(e)

if __name__ == "__main__":
    test_sapi_fuzz()
