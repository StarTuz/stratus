
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

def deep_dive():
    token = get_token()
    if not token: return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "StratusAI/2.0.0 (Windows NT 10.0; Win64; x64)" 
    }
    
    payload = {
        "sim": {
            "variables": {"PLANE LATITUDE": 34.0, "PLANE LONGITUDE": -118.0},
            "name": "StratusML", "version": "1.0"
        },
        "api_key": token
    }
    json_str = json.dumps(payload)

    # 1. Probe ttapi
    logger.info("1. Probing ttapi...")
    hosts = [
        "https://ttapi.stratus.ai",
        "https://ttdev.stratus.ai"
    ]
    for host in hosts:
        try:
            r = requests.get(host, headers=headers, timeout=2)
            logger.info(f"{host} -> {r.status_code}")
        except: pass
        
        # Try input endpoint
        try:
            r = requests.post(f"{host}/input", headers=headers, json=payload, timeout=2)
            logger.info(f"{host}/input -> {r.status_code}")
        except: pass

    # 2. SimAPI on apipri with User-Agent Spoof & Query Param
    logger.info("2. Probing apipri with Spoof & Query...")
    base_url = "https://apipri.stratus.ai/simapi/v1/input"
    
    # Try Query Param
    try:
        r = requests.post(base_url, headers=headers, params={"json": json_str}, timeout=5)
        logger.info(f"Query Param 'json': {r.status_code} {r.text[:50]}")
    except Exception as e: logger.error(e)

    # Try Query Param 'data'
    try:
        r = requests.post(base_url, headers=headers, params={"data": json_str}, timeout=5)
        logger.info(f"Query Param 'data': {r.status_code} {r.text[:50]}")
    except Exception as e: logger.error(e)

    # Try Multipart with Spoof
    try:
        files = {'json': ('simAPI_input.json', json_str, 'application/json')}
        r = requests.post(base_url, headers=headers, files=files, timeout=5)
        logger.info(f"Multipart Spoofed: {r.status_code} {r.text[:50]}")
    except Exception as e: logger.error(e)

if __name__ == "__main__":
    deep_dive()
