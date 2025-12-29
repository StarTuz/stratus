
import requests
import json
import logging
import os
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
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

def test_heartbeat():
    token = get_token()
    if not token: return
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 1. Start Flight (Just in case)
    requests.post(f"{SAPI_URL}/startFlight", params={"api_key": API_KEY_RO}, headers=headers, json={}, timeout=5)
    
    # 2. Telemetry Loop
    logger.info("Starting 30s Heartbeat Loop...")
    for i in range(30):
        try:
            payload = {
                "sim": {
                    "variables": {
                        "PLANE LATITUDE": 39.3200, 
                        "PLANE LONGITUDE": -120.1400,
                        "PLANE ALTITUDE": 5900,
                        "SIM ON GROUND": 1,
                        "LOCAL TIME": 12.0,
                        "ZULU TIME": 20.0,
                        "TITLE": "Cessna 172"
                    },
                    "name": "StratusML", "version": "1.0"
                },
                "api_key": API_KEY_RO # Try RO Key inside payload, Token in header
            }
            
            # Send to SAPI Input
            r = requests.post(f"{SAPI_URL}/v1/input", params={"api_key": API_KEY_RO}, headers=headers, json=payload, timeout=2)
            if i % 5 == 0: logger.info(f"   beat {i}: {r.status_code}")
            
            # Check Session every 5s
            if i % 5 == 0:
                r = requests.get(f"{SAPI_URL}/assignGate", params={"api_key": API_KEY_RO, "gate": "PARKING 1", "airport": "KTRK"}, headers=headers, timeout=2)
                if "No active flight" not in r.text:
                    logger.info(f"   SUCCESS! {r.text}")
                    break
                else:
                    logger.info("   Still no session...")
                    
        except Exception as e: logger.error(e)
        time.sleep(1)

if __name__ == "__main__":
    test_heartbeat()
