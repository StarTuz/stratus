
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

def check_status():
    token = get_token()
    if not token: return

    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    # List of likely endpoints to find current state
    endpoints = [
        "https://portal.stratus.ai/api/me",
        "https://portal.stratus.ai/api/user",
        "https://portal.stratus.ai/api/profile",
        "https://portal.stratus.ai/api/flights",
        "https://portal.stratus.ai/api/flight/active",
        "https://portal.stratus.ai/api/efb/status",
        "https://portal.stratus.ai/api/v1/status",
        "https://lambda.stratus.ai/user/status",
        "https://lambda.stratus.ai/flight/status"
    ]
    
    logger.info("Checking Status Endpoints...")
    
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            logger.info(f"GET {url} -> {r.status_code}")
            if r.status_code == 200:
                try:
                    logger.info(f"   Body: {json.dumps(r.json(), indent=2)[:300]}") # First 300 chars
                except:
                    logger.info(f"   Body: {r.text[:300]}")
        except Exception as e: logger.error(e)

if __name__ == "__main__":
    check_status()
