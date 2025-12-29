
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
API_KEY = "s4GH8119xFyX"
AUTH_URL = "https://lambda.stratus.ai/auth/login"
PORTAL_URL = "https://portal.stratus.ai/api/efb/submitFlightPlan"
SAPI_URL = "https://apipri.stratus.ai/sapi"

def get_token():
    if not USERNAME or not PASSWORD: return None
    try:
        r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
        return r.json().get("token")
    except: return None

def verify_session():
    token = get_token()
    if not token: return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 1. Submit Flight Plan (Trigger Session)
    payload = {
        "callsign": "N123AB",
        "aircraft": "C172",
        "origin": "KTRK",
        "destination": "KRNO",
        "departure_time": "1200",
        "enroute_time": "0030",
        "route": "DIRECT",
        "altitude": "7500",
        "flight_rules": "VFR",
        "email": USERNAME # Sending email just in case
    }
    
    logger.info("1. Submitting Flight Plan...")
    try:
        r = requests.post(PORTAL_URL, headers=headers, json=payload, timeout=5)
        logger.info(f"Submit Result: {r.status_code}")
    except Exception as e: logger.error(e)
    
    time.sleep(2) # Wait for backend sync

    # 2. Check SAPI Session
    logger.info("2. Checking SAPI Session (assignGate)...")
    try:
        # Include Token in SAPI headers too!
        sapi_headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        # And user's API key?
        params = {"api_key": API_KEY, "gate": "PARKING 1", "airport": "KTRK"}
        
        r = requests.get(f"{SAPI_URL}/assignGate", params=params, headers=sapi_headers, timeout=10)
        logger.info(f"SAPI Result: {r.status_code} {r.text}")
        
    except Exception as e: logger.error(e)

if __name__ == "__main__":
    verify_session()
