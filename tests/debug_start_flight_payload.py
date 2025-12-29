
import requests
import json
import logging
import os
import uuid
import time
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

USERNAME = os.environ.get("SI_USERNAME")
PASSWORD = os.environ.get("SI_PASSWORD")
API_KEY = "s4GH8119xFyX" # Config key
AUTH_URL = "https://lambda.stratus.ai/auth/login"
SAPI_URL = "https://apipri.stratus.ai/sapi"

def get_token():
    if not USERNAME or not PASSWORD: return None
    try:
        r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
        return r.json().get("token")
    except: return None

def test_start_flight_payload():
    token = get_token()
    if not token: return
    
    # Extract user ID (manual decode or just use what we saw)
    # Token "eyJ...eyJpZCI6ODQyNTA2..." -> id: 842506
    USER_ID = "842506"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Generate a random flight ID (integer) and UUID
    flight_id_int = random.randint(100000, 999999)
    flight_id_uuid = str(uuid.uuid4())
    
    # Payload 1: Matches flight.json structure
    payload_flight_json = {
        "flight_details": {
            "Email": USERNAME,
            "userid": USER_ID,
            "flight_id": flight_id_int,
            "api_key": API_KEY,
            "callsign": "N123AB",
            "tail_number": "N123AB"
        }
    }
    
    # Payload 2: Flat structure
    payload_flat = {
        "email": USERNAME,
        "userid": USER_ID,
        "flight_id": flight_id_int,
        "api_key": API_KEY
    }

    urls = [
        f"{SAPI_URL}/startFlight",
        f"{SAPI_URL}/v1/input", # Maybe input accepts flight details?
        "https://apipri.stratus.ai/simapi/v1/input" # Try here too
    ]
    
    for url in urls:
        logger.info(f"--- POST {url} ---")
        
        # Try Flight JSON Payload
        try:
            r = requests.post(url, headers=headers, json=payload_flight_json, timeout=5)
            logger.info(f"Payload (flight.json): {r.status_code} {r.text[:100]}")
        except Exception as e: logger.error(e)

        # Try Flat Payload
        try:
            r = requests.post(url, headers=headers, json=payload_flat, timeout=5)
            logger.info(f"Payload (Flat): {r.status_code} {r.text[:100]}")
        except Exception as e: logger.error(e)

    # Check if session exists after provided flight ID
    logger.info("--- Checking Session Existence ---")
    try:
        # We need to inject the flight ID into headers or params?
        # P2 Docs say flight_id is in flight.json.
        # Maybe X-Flight-ID header?
        check_headers = headers.copy()
        check_headers["X-Flight-ID"] = str(flight_id_int)
        
        r = requests.get(f"{SAPI_URL}/assignGate", params={"api_key": API_KEY, "gate": "PARKING 1", "airport": "KTRK"}, headers=check_headers)
        logger.info(f"assignGate (check): {r.status_code} {r.text}")
    except Exception as e: logger.error(e)

if __name__ == "__main__":
    test_start_flight_payload()
