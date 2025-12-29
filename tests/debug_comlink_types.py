
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
    r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    return r.json().get("token")

def test_comlink_types():
    token = get_token()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test all type values
    types = ["comlink", "efb", "vr", "client", "sim", "flight", "status", "user"]
    
    for t in types:
        url = f"https://lambda.stratus.ai/comlink?type={t}"
        try:
            r = requests.get(url, headers=headers, timeout=5)
            logger.info(f"type={t}: {r.status_code}")
            if r.status_code == 200 and len(r.text) > 0:
                # Check for useful data
                if "error" not in r.text.lower() and "Invalid" not in r.text:
                    logger.info(f"   RESPONSE: {r.text[:300]}")
                else:
                    logger.info(f"   Error: {r.text[:100]}")
        except Exception as e:
            logger.error(e)

if __name__ == "__main__":
    test_comlink_types()
