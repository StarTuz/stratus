
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

def get_token():
    if not USERNAME or not PASSWORD: return None
    try:
        r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
        return r.json().get("token")
    except: return None

def test_hosts():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "sim": {
            "variables": {"PLANE LATITUDE": 34.0, "PLANE LONGITUDE": -118.0, "TITLE": "Cessna 172"},
            "name": "StratusML", "version": "1.0"
        },
        "api_key": token
    }
    
    hosts = [
        "https://portal.stratus.ai",
        "https://lambda.stratus.ai",
        "https://api.stratus.ai",
        "https://stratus.ai"
    ]
    
    paths = [
        "/simapi/v1/input",
        "/api/sim/input",
        "/api/v1/input",
        "/input"
    ]

    for host in hosts:
        for path in paths:
            url = f"{host}{path}"
            logger.info(f"Trying {url}...")
            try:
                # Try JSON
                r = requests.post(url, headers=headers, json=payload, timeout=2)
                if r.status_code != 404:
                    logger.info(f"   [JSON] {r.status_code} {r.text[:100]}")
                
                # Try Multipart
                files = {'json': ('simAPI_input.json', json.dumps(payload), 'application/json')}
                r = requests.post(url, headers=headers, files=files, timeout=2)
                if r.status_code != 404:
                    logger.info(f"   [Multi] {r.status_code} {r.text[:100]}")
            except: pass

if __name__ == "__main__":
    test_hosts()
