
import requests
import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

USERNAME = os.environ.get("SI_USERNAME")
PASSWORD = os.environ.get("SI_PASSWORD")
API_KEY_RO = "s4GH8119xFyX"
AUTH_URL = "https://lambda.stratus.ai/auth/login"
SIMAPI_URL = "https://apipri.stratus.ai/simapi/v1/input"
SAPI_URL = "https://apipri.stratus.ai/sapi"

def get_token():
    r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    return r.json().get("token")

def test_flight_json_upload():
    token = get_token()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # The sidecar binary expects "flight.json"!
    payload = {
        "sim": {
            "variables": {
                "PLANE LATITUDE": 39.3200,
                "PLANE LONGITUDE": -120.1400,
                "PLANE ALTITUDE": 5900,
                "SIM ON GROUND": 1,
                "TITLE": "Cessna 172"
            },
            "name": "XPlane",  # Use XPlane since that's what the sidecar supports
            "version": "12.0"
        },
        "api_key": API_KEY_RO
    }
    json_str = json.dumps(payload)
    
    # Test 1: Multipart with filename "flight.json"
    logger.info("Test 1: Multipart field 'json' with filename 'flight.json'...")
    try:
        files = {'json': ('flight.json', json_str, 'application/json')}
        r = requests.post(SIMAPI_URL, headers=headers, files=files, timeout=5)
        logger.info(f"   Result: {r.status_code} {r.text}")
    except Exception as e:
        logger.error(e)
    
    # Test 2: Multipart with field name "flight.json"
    logger.info("Test 2: Multipart field 'flight.json'...")
    try:
        files = {'flight.json': ('flight.json', json_str, 'application/json')}
        r = requests.post(SIMAPI_URL, headers=headers, files=files, timeout=5)
        logger.info(f"   Result: {r.status_code} {r.text}")
    except Exception as e:
        logger.error(e)
    
    # Test 3: Multipart with field name "file" and filename "flight.json"
    logger.info("Test 3: Multipart field 'file' with filename 'flight.json'...")
    try:
        files = {'file': ('flight.json', json_str, 'application/json')}
        r = requests.post(SIMAPI_URL, headers=headers, files=files, timeout=5)
        logger.info(f"   Result: {r.status_code} {r.text}")
    except Exception as e:
        logger.error(e)
    
    # Test 4: Check session after uploads
    logger.info("\nChecking session...")
    r = requests.get(f"{SAPI_URL}/assignGate", params={"api_key": API_KEY_RO, "gate": "PARKING 1", "airport": "KTRK"}, headers=headers, timeout=5)
    logger.info(f"assignGate: {r.text}")

if __name__ == "__main__":
    test_flight_json_upload()
