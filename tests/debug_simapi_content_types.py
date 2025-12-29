
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

def fuzz_content_types():
    token = get_token()
    if not token: return
    
    auth_header = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "sim": {
            "variables": {"PLANE LATITUDE": 34.0, "PLANE LONGITUDE": -118.0, "TITLE": "Cessna 172"},
            "name": "StratusML", "version": "1.0"
        },
        "api_key": token
    }
    json_str = json.dumps(payload)
    
    tests = [
        # 1. Standard JSON
        ("application/json", json_str, "data"), 
        
        # 2. Text/Plain (sometimes used to bypass CORS/Parsers)
        ("text/plain", json_str, "data"),
        
        # 3. Form URL Encoded
        ("application/x-www-form-urlencoded", f"json={json_str}", "data"),
        ("application/x-www-form-urlencoded", list(payload.items()), "form"), # standard dict
        
        # 4. Binary/Stream
        ("application/octet-stream", json_str.encode('utf-8'), "data"),
        
        # 5. Custom header from some frameworks
        ("application/vnd.api+json", json_str, "data"),
    ]
    
    for ctype, data, mode in tests:
        h = auth_header.copy()
        h["Content-Type"] = ctype
        logger.info(f"Testing Content-Type: {ctype}...")
        
        try:
            if mode == "data":
                r = requests.post(SIMAPI_URL, headers=h, data=data, timeout=5)
            elif mode == "form":
                # requests handles encoding if we pass dict and NO content-type, but here we force it
                r = requests.post(SIMAPI_URL, headers=h, data=data, timeout=5)
                
            if "Missing JSON" not in r.text:
                logger.info(f"   SUCCESS? {r.status_code} {r.text[:100]}")
            else:
                logger.info(f"   Fail: {r.status_code} {r.text[:50]}")
        except Exception as e: logger.error(e)

if __name__ == "__main__":
    fuzz_content_types()
