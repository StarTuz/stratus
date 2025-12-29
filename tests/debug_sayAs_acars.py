
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

API_KEY = "s4GH8119xFyX"
BASE_URL = "https://apipri.stratus.ai/sapi/sayAs"

def test_acars_in():
    logger.info(f"Testing ACARS_IN with Key: {API_KEY[:4]}...")
    
    # Docs: "ACARS_IN" channel, 128 max chars, dedicated fields
    params = {
        "api_key": API_KEY,
        "channel": "ACARS_IN",
        "message": "TEST MESSAGE 1",
        "from": "DISPATCH",
        "response_code": "WU",
        "message_type": "cpdlc"
    }
    
    try:
        logger.info(f"GET request to {BASE_URL}...")
        r = requests.get(BASE_URL, params=params, timeout=10)
        logger.info(f"Status: {r.status_code}")
        logger.info(f"Body: {r.text}")
        
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    test_acars_in()
