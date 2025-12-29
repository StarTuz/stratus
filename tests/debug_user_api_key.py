
import requests
import json
import logging
import os
import base64

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

USERNAME = os.environ.get("SI_USERNAME")
PASSWORD = os.environ.get("SI_PASSWORD")
AUTH_URL = "https://lambda.stratus.ai/auth/login"

def get_token_and_decode():
    if not USERNAME or not PASSWORD: return None
    try:
        r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
        data = r.json()
        token = data.get("token")
        
        if token:
            # Decode JWT payload (middle part)
            parts = token.split(".")
            if len(parts) == 3:
                # Add padding if needed
                payload = parts[1]
                payload += "=" * (4 - len(payload) % 4)
                decoded = json.loads(base64.urlsafe_b64decode(payload))
                logger.info(f"JWT Payload:\n{json.dumps(decoded, indent=2)}")
                return decoded
    except Exception as e:
        logger.error(f"Error: {e}")
    return None

def search_for_api_key():
    decoded = get_token_and_decode()
    if not decoded:
        return
    
    # Check if there's an api_key or similar field
    interesting_fields = ["api_key", "apiKey", "key", "productId", "id", "accountType"]
    for field in interesting_fields:
        if field in decoded:
            logger.info(f"Found '{field}': {decoded[field]}")
    
    # Try to get user data from lambda
    token = None
    r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    token = r.json().get("token")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Endpoints that might return the real API key
    endpoints = [
        "https://lambda.stratus.ai/user/apikey",
        "https://lambda.stratus.ai/apikey",
        "https://lambda.stratus.ai/key",
        "https://lambda.stratus.ai/user/key",
        "https://portal.stratus.ai/api/apikey",
        "https://portal.stratus.ai/api/user/key",
    ]
    
    logger.info("\nSearching for API Key endpoints...")
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=3)
            if r.status_code == 200:
                logger.info(f"FOUND: {url} -> {r.text[:200]}")
            elif r.status_code != 404:
                logger.info(f"{url} -> {r.status_code}")
        except: pass

if __name__ == "__main__":
    search_for_api_key()
