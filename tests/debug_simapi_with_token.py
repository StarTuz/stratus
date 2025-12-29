
import requests
import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

USERNAME = os.environ.get("SI_USERNAME")
PASSWORD = os.environ.get("SI_PASSWORD")
AUTH_URL = "https://lambda.stratus.ai/auth/login"
SIMAPI_URL = "https://apipri.stratus.ai/simapi/v1/input"

def get_token():
    if not USERNAME or not PASSWORD:
        return None
    try:
        r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
        return r.json().get("token")
    except:
        return None

def test_simapi():
    token = get_token()
    if not token:
        return

    logger.info("Testing SimAPI with Auth Token...")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "sim": {
            "variables": {"PLANE LATITUDE": 34.0, "PLANE LONGITUDE": -118.0},
            "name": "StratusML",
            "version": "1.0"
        }
    }
    
    # Test 1: Multipart 'json' with Token Header
    try:
        files = {'json': (None, json.dumps(payload), 'application/json')}
        r = requests.post(SIMAPI_URL, headers=headers, files=files, timeout=5)
        logger.info(f"Multipart 'json' + Bearer -> {r.status_code} {r.text}")
    except Exception as e: logger.error(e)

    # Test 2: Multipart 'json' with api_key=token param
    try:
        files = {'json': (None, json.dumps(payload), 'application/json')}
        r = requests.post(SIMAPI_URL, params={"api_key": token}, files=files, timeout=5)
        logger.info(f"Multipart 'json' + api_key=token -> {r.status_code} {r.text}")
    except Exception as e: logger.error(e)

if __name__ == "__main__":
    test_simapi()
