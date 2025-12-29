
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

def test_userid_param():
    token = get_token()
    if not token: return
    
    headers = {"Authorization": f"Bearer {token}"}
    USER_ID = "842506"
    
    # Test assignGate with userid instead of api_key
    tests = [
        {"userid": USER_ID, "gate": "PARKING 1", "airport": "KTRK"},
        {"user_id": USER_ID, "gate": "PARKING 1", "airport": "KTRK"},
        {"id": USER_ID, "gate": "PARKING 1", "airport": "KTRK"},
        {"api_key": API_KEY_RO, "userid": USER_ID, "gate": "PARKING 1", "airport": "KTRK"},
    ]
    
    logger.info("Testing assignGate with various ID params...")
    for params in tests:
        try:
            r = requests.get(f"{SAPI_URL}/assignGate", params=params, headers=headers, timeout=5)
            label = ", ".join(f"{k}={v[:10]}" for k,v in params.items() if k != "gate" and k != "airport")
            logger.info(f"[{label}] -> {r.status_code} {r.text[:80]}")
        except Exception as e: logger.error(e)

if __name__ == "__main__":
    test_userid_param()
