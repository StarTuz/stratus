
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
USER_ID = "842506"
AUTH_URL = "https://lambda.stratus.ai/auth/login"
SAPI_URL = "https://apipri.stratus.ai/sapi"

def get_token():
    r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    return r.json().get("token")

def test_siai_commands():
    token = get_token()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Commands found in the binary
    commands = [
        # setVar - might set session variables
        ("POST", f"{SAPI_URL}/setVar", {"name": "SIAI_COPILOT", "value": 1}),
        ("POST", f"{SAPI_URL}/setVar", {"name": "SIAI_ATC_MASTER_OFF", "value": 0}),
        ("POST", f"{SAPI_URL}/setVar", {"userid": USER_ID}),
        
        # pingNow - might establish session presence
        ("POST", f"{SAPI_URL}/pingNow", {}),
        ("POST", f"{SAPI_URL}/pingNow", {"userid": USER_ID}),
        ("POST", f"{SAPI_URL}/ping", {}),
        
        # Client registration
        ("POST", f"{SAPI_URL}/register", {"userid": USER_ID, "client": "StratusML"}),
        ("POST", f"{SAPI_URL}/client/register", {"userid": USER_ID}),
        ("POST", f"{SAPI_URL}/session/start", {"userid": USER_ID}),
        
        # Connect with full payload
        ("POST", f"{SAPI_URL}/connect", {"userid": USER_ID, "api_key": API_KEY_RO, "sim": "xplane"}),
    ]
    
    for method, url, body in commands:
        try:
            params = {"api_key": API_KEY_RO}
            r = requests.post(url, headers=headers, params=params, json=body, timeout=3)
            if r.status_code != 404:
                logger.info(f"{method} {url.split('/')[-1]}: {r.status_code} {r.text[:80]}")
        except Exception as e:
            pass
    
    # Check session
    logger.info("\nChecking session...")
    r = requests.get(f"{SAPI_URL}/assignGate", params={"api_key": API_KEY_RO, "gate": "PARKING 1", "airport": "KTRK"}, headers=headers, timeout=5)
    logger.info(f"assignGate: {r.text}")

if __name__ == "__main__":
    test_siai_commands()
