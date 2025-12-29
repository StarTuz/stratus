
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
SAPI_URL = "https://apipri.stratus.ai/sapi"

def get_token():
    r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    return r.json().get("token")

def test_efb_flow():
    """
    Replicate the exact EFB flow from Stratus.js:
    1. comlink?type=efb - get session status
    2. submitFlightPlan - send flight plan (MSFS format)
    3. Check if session is established
    """
    token = get_token()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Step 1: Check comlink status (EFB mode)
    logger.info("Step 1: Checking EFB comlink status...")
    try:
        r = requests.get("https://lambda.stratus.ai/comlink?type=efb", headers=headers, timeout=5)
        logger.info(f"   Comlink: {r.status_code}")
        if r.status_code == 200:
            logger.info(f"   Response: {r.text[:200]}")
    except Exception as e:
        logger.error(e)
    
    # Step 2: Submit Flight Plan (MSFS-compatible structure)
    # Based on what Coherent.call('GET_FLIGHTPLAN') returns
    flightplan = {
        "cruiseAltitude": 5500,
        "origin": {
            "icao": "KLAX",
            "name": "Los Angeles International"
        },
        "destination": {
            "icao": "KSFO", 
            "name": "San Francisco International"
        },
        "departureRunway": "25L",
        "arrivalRunway": "28R",
        "waypoints": [
            {"icao": "KLAX", "lat": 33.9425, "lon": -118.4081},
            {"icao": "VNY", "lat": 34.2098, "lon": -118.4896},
            {"icao": "KSFO", "lat": 37.6213, "lon": -122.3790}
        ],
        "aircraft": {
            "type": "C172",
            "callsign": "N123ML"
        }
    }
    
    logger.info("Step 2: Submitting flight plan (EFB style)...")
    try:
        r = requests.post(
            "https://portal.stratus.ai/api/efb/submitFlightPlan",
            headers=headers,
            json=flightplan,
            timeout=10
        )
        logger.info(f"   submitFlightPlan: {r.status_code}")
        if r.text:
            logger.info(f"   Response: {r.text[:200]}")
    except Exception as e:
        logger.error(e)
    
    # Step 3: Check if session is now active
    logger.info("\nStep 3: Checking session...")
    r = requests.get(f"{SAPI_URL}/assignGate", 
                    params={"api_key": API_KEY, "gate": "GATE A1", "airport": "KLAX"}, 
                    headers=headers, timeout=5)
    logger.info(f"   assignGate: {r.text}")
    
    # Step 4: Also try sayAs at LAX
    logger.info("\nStep 4: Attempting sayAs...")
    r = requests.get(f"{SAPI_URL}/sayAs",
                    params={
                        "api_key": API_KEY,
                        "channel": "COM1",
                        "message": "Los Angeles Ground Cessna 123ML radio check",
                        "rephrase": "0"
                    },
                    headers=headers, timeout=10)
    logger.info(f"   sayAs: {r.text[:200]}")

if __name__ == "__main__":
    test_efb_flow()
