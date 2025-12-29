
import requests
import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

API_KEY = "s4GH8119xFyX"
# Valid Flight ID from our dummy flight.json
FLIGHT_ID = "123456" 
BASE_URL = "https://apipri.stratus.ai/sapi"

def test_flight_id_injection():
    logger.info(f"Testing Flight ID injection: {FLIGHT_ID}")
    
    # Common headers
    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json"
    }

    # 1. Test as Query Param
    logger.info("\n--- Test 1: Query Param ---")
    try:
        url = f"{BASE_URL}/assignGate"
        params = {"api_key": API_KEY, "gate": "A1", "airport": "KTRK", "flight_id": FLIGHT_ID}
        r = requests.get(url, params=params, headers=headers, timeout=5)
        logger.info(f"Result: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"Error: {e}")

    # 2. Test as Header (X-Flight-ID)
    logger.info("\n--- Test 2: Header X-Flight-ID ---")
    try:
        url = f"{BASE_URL}/assignGate"
        params = {"api_key": API_KEY, "gate": "A1", "airport": "KTRK"}
        headers_x = headers.copy()
        headers_x["X-Flight-ID"] = FLIGHT_ID
        r = requests.get(url, params=params, headers=headers_x, timeout=5)
        logger.info(f"Result: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"Error: {e}")

    # 3. Test as Header (Flight-ID)
    logger.info("\n--- Test 3: Header Flight-ID ---")
    try:
        url = f"{BASE_URL}/assignGate"
        params = {"api_key": API_KEY, "gate": "A1", "airport": "KTRK"}
        headers_f = headers.copy()
        headers_f["Flight-ID"] = FLIGHT_ID
        r = requests.get(url, params=params, headers=headers_f, timeout=5)
        logger.info(f"Result: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"Error: {e}")

    # 4. Test as Header (X-Session-ID) - Wild guess
    logger.info("\n--- Test 4: Header X-Session-ID ---")
    try:
        url = f"{BASE_URL}/assignGate"
        params = {"api_key": API_KEY, "gate": "A1", "airport": "KTRK"}
        headers_s = headers.copy()
        headers_s["X-Session-ID"] = FLIGHT_ID
        r = requests.get(url, params=params, headers=headers_s, timeout=5)
        logger.info(f"Result: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    test_flight_id_injection()
