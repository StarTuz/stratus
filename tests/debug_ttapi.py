
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

def test_ttapi():
    token = get_token()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # ttapi - Traffic Tracker API - found in sidecar binary
    ttapi_urls = [
        "https://ttapi.stratus.ai/",
        "https://ttapi.stratus.ai/input",
        "https://ttapi.stratus.ai/telemetry",
        "https://ttapi.stratus.ai/api/input",
        "https://ttapi.stratus.ai/v1/input",
    ]
    
    telemetry = {
        "name": "StratusML",
        "version": "1.0.0",
        "adapter_version": "1.0.0",
        "simapi_version": "1.0",
        "exe": "xplane12.exe",
        "api_key": API_KEY,
        "variables": {
            "PLANE LATITUDE": 33.9425,
            "PLANE LONGITUDE": -118.4081,
            "PLANE ALTITUDE": 125,
            "SIM ON GROUND": 1,
            "TITLE": "Cessna 172"
        }
    }
    
    logger.info("Testing ttapi.stratus.ai endpoints...")
    for url in ttapi_urls:
        try:
            r = requests.post(url, headers=headers, json=telemetry, timeout=3)
            logger.info(f"POST {url} -> {r.status_code} {r.text[:100] if r.text else ''}")
        except Exception as e:
            logger.info(f"POST {url} -> Error: {str(e)[:50]}")
    
    # Test sidecar debug endpoint
    logger.info("\nTesting sidecar_debug endpoint...")
    try:
        r = requests.post("https://portal.stratus.ai/api/sidecar_debug", 
                         headers=headers, json={"action": "status"}, timeout=5)
        logger.info(f"sidecar_debug: {r.status_code} {r.text[:200] if r.text else ''}")
    except Exception as e:
        logger.error(f"Error: {e}")
    
    # Check session
    logger.info("\nChecking session...")
    r = requests.get(f"{SAPI_URL}/assignGate", 
                    params={"api_key": API_KEY, "gate": "GATE A1", "airport": "KLAX"}, 
                    headers=headers, timeout=5)
    logger.info(f"assignGate: {r.text}")

if __name__ == "__main__":
    test_ttapi()
