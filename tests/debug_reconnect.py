
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
SAPI_URL = "https://apipri.stratus.ai/sapi"

def get_token():
    r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    return r.json().get("token")

def test_reconnect():
    token = get_token()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test various endpoints that might handle the RECONNECT event
    endpoints = [
        # Try sendCallBackEvent on different hosts
        ("POST", "https://lambda.stratus.ai/sendCallBackEvent", {"event": "RECONNECT"}),
        ("GET", "https://lambda.stratus.ai/sendCallBackEvent?event=RECONNECT", None),
        ("POST", "https://apipri.stratus.ai/sapi/sendCallBackEvent", {"event": "RECONNECT"}),
        ("GET", "https://apipri.stratus.ai/sapi/sendCallBackEvent?event=RECONNECT", None),
        ("POST", "https://portal.stratus.ai/api/sendCallBackEvent", {"event": "RECONNECT"}),
        
        # Direct callback/reconnect endpoints
        ("POST", "https://lambda.stratus.ai/callback", {"event": "RECONNECT"}),
        ("POST", "https://lambda.stratus.ai/reconnect", {}),
        ("POST", "https://apipri.stratus.ai/sapi/reconnect", {}),
        ("POST", "https://apipri.stratus.ai/sapi/connect", {}),
        
        # Event endpoints
        ("POST", "https://lambda.stratus.ai/event", {"event": "RECONNECT"}),
        ("POST", "https://apipri.stratus.ai/sapi/event", {"event": "RECONNECT"}),
    ]
    
    for method, url, body in endpoints:
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=3)
            else:
                r = requests.post(url, headers=headers, json=body, timeout=3)
            
            if r.status_code != 404:
                logger.info(f"{method} {url} -> {r.status_code} {r.text[:100]}")
        except Exception as e:
            pass  # Skip timeouts
    
    # Now check if session was established
    logger.info("\nChecking session after RECONNECT attempts...")
    r = requests.get(f"{SAPI_URL}/assignGate", params={"api_key": API_KEY_RO, "gate": "PARKING 1", "airport": "KTRK"}, headers=headers, timeout=5)
    logger.info(f"assignGate: {r.status_code} {r.text}")

if __name__ == "__main__":
    test_reconnect()
