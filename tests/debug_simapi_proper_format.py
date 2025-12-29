
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
SIMAPI_URL = "https://apipri.stratus.ai/simapi/v1/input"
SAPI_URL = "https://apipri.stratus.ai/sapi"

def get_token():
    r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    return r.json().get("token")

def test_proper_simapi_format():
    token = get_token()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # According to docs, SimAPI requires these 5 fields PLUS simvars
    payload = {
        "name": "StratusML",
        "version": "1.0.0",
        "adapter_version": "1.0.0", 
        "simapi_version": "1.0",
        "exe": "xplane12.exe",
        "variables": {
            "PLANE LATITUDE": 33.9425,  # LAX coordinates
            "PLANE LONGITUDE": -118.4081,
            "PLANE ALTITUDE": 125,
            "PLANE HEADING DEGREES TRUE": 90.0,
            "SIM ON GROUND": 1,
            "AIRSPEED INDICATED": 0,
            "VERTICAL SPEED": 0,
            "COM ACTIVE FREQUENCY:1": 121.9,
            "COM STANDBY FREQUENCY:1": 127.0,
            "TRANSPONDER CODE:1": 1200,
            "TITLE": "Cessna 172 Skyhawk",
            "LOCAL TIME": 43200,  # Noon
            "ZULU TIME": 72000    # 20:00Z
        },
        "api_key": API_KEY
    }
    
    json_str = json.dumps(payload)
    
    # Test 1: Raw JSON body with proper Content-Type
    logger.info("Test 1: Raw JSON body...")
    try:
        r = requests.post(SIMAPI_URL, headers={**headers, "Content-Type": "application/json"}, data=json_str, timeout=5)
        logger.info(f"   Result: {r.status_code} {r.text[:100]}")
    except Exception as e:
        logger.error(e)
    
    # Test 2: Multipart with filename simAPI_telemetry.json (the actual file name used)
    logger.info("Test 2: Multipart simAPI_telemetry.json...")
    try:
        files = {'file': ('simAPI_telemetry.json', json_str, 'application/json')}
        r = requests.post(SIMAPI_URL, headers=headers, files=files, timeout=5)
        logger.info(f"   Result: {r.status_code} {r.text[:100]}")
    except Exception as e:
        logger.error(e)
    
    # Test 3: Multipart with field name matching the file structure
    logger.info("Test 3: Multipart json field with simAPI_telemetry.json filename...")
    try:
        files = {'json': ('simAPI_telemetry.json', json_str, 'application/json')}
        r = requests.post(SIMAPI_URL, headers=headers, files=files, timeout=5)
        logger.info(f"   Result: {r.status_code} {r.text[:100]}")
    except Exception as e:
        logger.error(e)
    
    # Check session after all attempts
    logger.info("\nChecking session at LAX...")
    r = requests.get(f"{SAPI_URL}/assignGate", params={"api_key": API_KEY, "gate": "GATE A1", "airport": "KLAX"}, headers=headers, timeout=5)
    logger.info(f"assignGate: {r.text}")

if __name__ == "__main__":
    test_proper_simapi_format()
