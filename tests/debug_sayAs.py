
import requests
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

API_KEY = "s4GH8119xFyX"
BASE_URL = "https://apipri.stratus.ai/sapi/sayAs"

def test_say_as():
    logger.info(f"Testing sayAs with Key: {API_KEY[:4]}...")
    
    params = {
        "api_key": API_KEY,
        "channel": "COM1",
        "message": "Radio Check 1 2 3",
        "rephrase": 0
    }
    
    try:
        # User documentation says GET request for sayAs
        logger.info(f"POST request to {BASE_URL}...")
        r = requests.post(BASE_URL, params={"api_key": API_KEY}, json=params, timeout=10)
        logger.info(f"POST Status: {r.status_code}")
        logger.info(f"POST Body: {r.text}")

        # Try GET as per docs "Examples" section just in case
        logger.info(f"GET request to {BASE_URL}...")
        r_get = requests.get(BASE_URL, params=params, timeout=10)
        logger.info(f"GET Status: {r_get.status_code}")
        logger.info(f"GET Body: {r_get.text}")
        
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    test_say_as()
