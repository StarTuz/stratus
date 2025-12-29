
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

def test_session_cookies():
    s = requests.Session()
    
    # 1. Login
    try:
        r = s.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
        token = r.json().get("token")
        if not token: return
        logger.info("Login Successful")
    except: return

    headers_auth = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    headers_sapi = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    # Update Session Headers
    s.headers.update(headers_sapi)

    # 2. Submit Flight Plan
    payload_plan = {
        "callsign": "N123AB",
        "aircraft": "C172",
        "origin": "KTRK",
        "destination": "KRNO",
        "departure_time": "1200",
        "flight_rules": "VFR"
    }
    logger.info("2. Submitting Flight Plan...")
    try:
        r = s.post(PORTAL_URL, headers=headers_auth, json=payload_plan, timeout=10)
        logger.info(f"Plan Result: {r.status_code}")
        logger.info(f"Cookies after Plan: {s.cookies.get_dict()}")
    except Exception as e: logger.error(e)

    time.sleep(1)

    # 3. Start Flight
    logger.info("3. Starting Flight (SAPI)...")
    try:
        r = s.post(f"{SAPI_URL}/startFlight", params={"api_key": API_KEY}, json={}, timeout=10)
        logger.info(f"StartFlight Result: {r.status_code}")
        logger.info(f"Cookies after StartFlight: {s.cookies.get_dict()}")
    except Exception as e: logger.error(e)

    time.sleep(1)

    # 4. Telemetry
    logger.info("4. Sending Telemetry (SAPI)...")
    try:
        telemetry = {
            "sim": {
              "variables": {
                 "PLANE LATITUDE": 39.3200, 
                 "PLANE LONGITUDE": -120.1400,
                 "PLANE ALTITUDE": 5900,
                 "SIM ON GROUND": 1,
                 "TITLE": "Cessna 172"
              },
              "name": "StratusML",
              "version": "1.0"
            },
            "api_key": API_KEY
        }
        r = s.post(f"{SAPI_URL}/v1/input", params={"api_key": API_KEY}, json=telemetry, timeout=5)
        logger.info(f"Telemetry Result: {r.status_code}")
    except Exception as e: logger.error(e)

    time.sleep(1)

    # 5. Assign Gate
    logger.info("5. Assigning Gate...")
    try:
        r = s.get(f"{SAPI_URL}/assignGate", params={"api_key": API_KEY, "gate": "PARKING 1", "airport": "KTRK"}, timeout=10)
        logger.info(f"AssignGate Result: {r.status_code} Body: {r.text}")
    except Exception as e: logger.error(e)

if __name__ == "__main__":
    test_session_cookies()
