
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
    if not USERNAME or not PASSWORD:
        return None
    try:
        r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
        if r.status_code == 200:
            return r.json().get("token")
    except:
        return None
    return None

def test_token_usage():
    token = get_token()
    if not token:
        logger.error("Failed to get token")
        return

    logger.info(f"Token obtained: {token[:10]}...")

    # 1. Test Lambda Comlink
    url = "https://lambda.stratus.ai/comlink"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        logger.info(f"GET {url} -> {r.status_code} {r.text[:200]}")
    except Exception as e: logger.error(e)

    try:
        r = requests.get(f"{url}?type=efb", headers=headers, timeout=5)
        logger.info(f"GET {url}?type=efb -> {r.status_code} {r.text[:200]}")
    except Exception as e: logger.error(e)

    # 2. Test SAPI StartFlight with Bearer
    url = "https://apipri.stratus.ai/sapi/startFlight"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.post(url, headers=headers, json={}, timeout=5) # try POST
        logger.info(f"POST {url} (Bearer) -> {r.status_code} {r.text[:200]}")
    except Exception as e: logger.error(e)
    
    # 3. Test SAPI StartFlight with Token as API Key
    try:
        r = requests.post(url, params={"api_key": token}, json={}, timeout=5)
        logger.info(f"POST {url} (Token as Key) -> {r.status_code} {r.text[:200]}")
    except Exception as e: logger.error(e)

    # 4. Test User Info on Portal
    url = "https://portal.stratus.ai/api/user"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        logger.info(f"GET {url} -> {r.status_code} {r.text[:200]}")
    except Exception as e: logger.error(e)

if __name__ == "__main__":
    test_token_usage()
