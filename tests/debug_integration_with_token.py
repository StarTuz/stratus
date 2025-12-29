
import requests
import json
import logging
import os
import time
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

USERNAME = os.environ.get("SI_USERNAME")
PASSWORD = os.environ.get("SI_PASSWORD")
API_KEY = "s4GH8119xFyX" # Read-only key from config
AUTH_URL = "https://lambda.stratus.ai/auth/login"
SAPI_URL = "https://apipri.stratus.ai/sapi"

def get_token():
    if not USERNAME or not PASSWORD:
        return None
    try:
        r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
        if r.status_code == 200:
            return r.json().get("token")
    except:
        return None
    return None

def test_integration_with_token():
    token = get_token()
    if not token:
        logger.error("Failed to get token")
        return

    logger.info("Token obtained. Starting Integration Test...")

    # Headers for SAPI: Bearer Token AND API Key
    headers = {
        "Authorization": f"Bearer {token}",
        "X-API-Key": API_KEY, # Just in case
        "Accept": "application/json"
    }
    
    # Common Params (API Key is often a query param too)
    params = {"api_key": API_KEY}

    # 1. Start Flight
    logger.info("1. Calling startFlight...")
    try:
        # P2 Docs say startFlight might not need a body? sending empty json
        r = requests.post(f"{SAPI_URL}/startFlight", params=params, headers=headers, json={}, timeout=10)
        logger.info(f"startFlight Result: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"startFlight failed: {e}")

    # 2. Assign Gate (Truckee Test)
    logger.info("2. Calling assignGate (KTRK)...")
    try:
        gate_params = params.copy()
        gate_params.update({"gate": "PARKING 1", "airport": "KTRK"})
        r = requests.get(f"{SAPI_URL}/assignGate", params=gate_params, headers=headers, timeout=10)
        logger.info(f"assignGate Result: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"assignGate failed: {e}")

    # 3. Telemetry Loop (Background)
    # We need to see if sapi/v1/input accepts the token and updates the session
    def send_telemetry():
        logger.info("   -> Starting Telemetry Loop...")
        telemetry_url = f"{SAPI_URL}/v1/input"
        
        # Telemetry Payload (Example)
        payload = {
           "sim": {
              "variables": {
                 "PLANE LATITUDE": 39.3200, # Truckee
                 "PLANE LONGITUDE": -120.1400,
                 "PLANE ALTITUDE": 5900,
                 "SIM ON GROUND": 1,
                 "AIRSPEED INDICATED": 0,
                 "LOCAL TIME": 12.0,
                 "ZULU TIME": 20.0,
                  "TITLE": "Cessna 172"
              },
              "name": "StratusML",
              "version": "1.0"
           },
           "api_key": API_KEY # Often payload needs key too
        }

        for i in range(5):
            try:
                # Send with Token Header
                r = requests.post(telemetry_url, params=params, headers=headers, json=payload, timeout=5)
                # logger.info(f"   Telemetry {i} Result: {r.status_code}") # Silent unless error
                if r.status_code != 200 or "error" in r.text.lower():
                     logger.warning(f"   Telemetry {i} Error: {r.status_code} - {r.text}")
            except Exception as e:
                logger.error(f"   Telemetry error: {e}")
            time.sleep(1)

    t = threading.Thread(target=send_telemetry)
    t.start()
    
    # 4. Check Comms History (Radio Check)
    # If session is active, we should see updates or at least no "No active flight" error
    time.sleep(2)
    logger.info("3. Calling sayAs (Radio Check)...")
    try:
        p = params.copy()
        p.update({"channel": "COM1", "message": "Truckee Traffic, N123AB radio check", "rephrase": "0"})
        r = requests.get(f"{SAPI_URL}/sayAs", params=p, headers=headers, timeout=10)
        logger.info(f"sayAs Result: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"sayAs failed: {e}")
        
    t.join()

if __name__ == "__main__":
    test_integration_with_token()
