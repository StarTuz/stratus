
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

def test_full_sequence():
    token = get_token()
    if not token: return

    headers_auth = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    headers_sapi = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    # 1. Submit Flight Plan
    payload_plan = {
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
    logger.info("1. Submitting Flight Plan...")
    try:
        r = requests.post(PORTAL_URL, headers=headers_auth, json=payload_plan, timeout=10)
        logger.info(f"Plan Result: {r.status_code} Body: {r.text}")
    except Exception as e: logger.error(e)

    time.sleep(1)

    # 2. Start Flight
    logger.info("2. Starting Flight (SAPI)...")
    try:
        # P2 says use api_key param
        r = requests.post(f"{SAPI_URL}/startFlight", params={"api_key": API_KEY}, headers=headers_sapi, json={}, timeout=10)
        logger.info(f"StartFlight Result: {r.status_code} Body: {r.text}")
    except Exception as e: logger.error(e)

    time.sleep(1)

    # 3. Telemetry (SAPI Input - since SimAPI fails)
    logger.info("3. Sending Telemetry (SAPI)...")
    try:
        telemetry = {
            "sim": {
              "variables": {
                 "PLANE LATITUDE": 39.3200, 
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
            "api_key": API_KEY
        }
        r = requests.post(f"{SAPI_URL}/v1/input", params={"api_key": API_KEY}, headers=headers_sapi, json=telemetry, timeout=5)
        logger.info(f"Telemetry Result: {r.status_code} Body: {r.text}")
    except Exception as e: logger.error(e)

    time.sleep(1)

    # 4. Assign Gate
    logger.info("4. Assigning Gate...")
    try:
        r = requests.get(f"{SAPI_URL}/assignGate", params={"api_key": API_KEY, "gate": "PARKING 1", "airport": "KTRK"}, headers=headers_sapi, timeout=10)
        logger.info(f"AssignGate Result: {r.status_code} Body: {r.text}")
    except Exception as e: logger.error(e)

if __name__ == "__main__":
    test_full_sequence()
