
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
    if not USERNAME or not PASSWORD: return None
    try:
        r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
        return r.json().get("token")
    except: return None

def test_simapi_raw():
    token = get_token()
    if not token: return
    
    headers = {"Authorization": f"Bearer {token}"} # Content-Type auto-added by requests
    
    payload = {
        "sim": {
            "variables": {
                "PLANE LATITUDE": 34.0, 
                "PLANE LONGITUDE": -118.0,
                "TITLE": "Cessna 172"
            },
            "name": "StratusML",
            "version": "1.0"
        },
        "api_key": token 
    }
    
    logger.info("Testing SimAPI with Raw JSON + Token...")
    
    # Test 1: JSON Body
    try:
        r = requests.post(SIMAPI_URL, headers=headers, json=payload, timeout=5)
        logger.info(f"JSON Body: {r.status_code} {r.text}")
    except Exception as e: logger.error(e)

    # Test 2: Form URL Encoded 'json' field
    try:
        r = requests.post(SIMAPI_URL, headers=headers, data={"json": json.dumps(payload)}, timeout=5)
        logger.info(f"Form-UrlEncoded 'json': {r.status_code} {r.text}")
    except Exception as e: logger.error(e)

if __name__ == "__main__":
    test_simapi_raw()
