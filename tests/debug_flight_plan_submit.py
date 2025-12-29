
import requests
import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

USERNAME = os.environ.get("SI_USERNAME")
PASSWORD = os.environ.get("SI_PASSWORD")
API_KEY = "s4GH8119xFyX"
AUTH_URL = "https://lambda.stratus.ai/auth/login"

def get_token():
    if not USERNAME or not PASSWORD: return None
    try:
        r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
        return r.json().get("token")
    except: return None

def test_flight_plan():
    token = get_token()
    if not token: return
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Flight Plan Payload (Guessing fields based on standard SimBrief/EFB formats)
    payload = {
        "callsign": "N123AB",
        "aircraft": "C172",
        "origin": "KTRK",
        "destination": "KRNO",
        "departure_time": "1200",
        "enroute_time": "0030",
        "route": "DIRECT",
        "altitude": "7500",
        "flight_rules": "VFR"
    }
    
    urls = [
        "https://portal.stratus.ai/api/efb/submitFlightPlan",
        "https://portal.stratus.ai/api/postFlightPlan",
        "https://portal.stratus.ai/api/flight/new",
        "https://portal.stratus.ai/api/flights"
    ]
    
    for url in urls:
        logger.info(f"--- POST {url} ---")
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=5)
            logger.info(f"{r.status_code} {r.text[:100]}")
        except Exception as e: logger.error(e)

if __name__ == "__main__":
    test_flight_plan()
