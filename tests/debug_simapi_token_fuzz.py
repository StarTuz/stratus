
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

def fuzz_simapi():
    token = get_token()
    if not token: return
    
    headers = {"Authorization": f"Bearer {token}"}
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
        "api_key": token # Try token as key
    }
    json_str = json.dumps(payload)
    
    field_names = [
        "json", "data", "file", "payload", "input", 
        "simAPI_input", "simAPI_input.json", "simapi_input",
        "json_file", "upload", "telemetry"
    ]
    
    for name in field_names:
        try:
            files = {name: ('simAPI_input.json', json_str, 'application/json')}
            r = requests.post(SIMAPI_URL, headers=headers, files=files, timeout=5)
            logger.info(f"Field '{name}': {r.status_code} {r.text[:50]}")
        except Exception as e:
            logger.error(f"Field '{name}' error: {e}")

if __name__ == "__main__":
    fuzz_simapi()
