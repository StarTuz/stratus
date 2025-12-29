
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
BASE_URL = "https://lambda.stratus.ai"

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

def fuzz_lambda():
    token = get_token()
    if not token:
        logger.error("Failed to get token")
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    endpoints = [
        ("GET", "/user"),
        ("GET", "/me"),
        ("GET", "/profile"),
        ("GET", "/flight"),
        ("GET", "/flights"),
        ("POST", "/flight/start"),
        ("POST", "/flight/create"),
        ("GET", "/history"),
        ("GET", "/sim"),
        ("POST", "/connect"),
        ("GET", "/api/user"),
        ("GET", "/auth/user")
    ]

    for method, path in endpoints:
        url = f"{BASE_URL}{path}"
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=5)
            else:
                r = requests.post(url, headers=headers, json={}, timeout=5)
            
            logger.info(f"{method} {path} -> {r.status_code}")
            if r.status_code == 200:
                logger.info(f"Response: {r.text[:200]}")
        except Exception as e:
            logger.error(f"Error {method} {path}: {e}")

if __name__ == "__main__":
    fuzz_lambda()
