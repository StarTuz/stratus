
import requests
import configparser
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def load_api_key():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config.get('sapi', 'api_key')

API_KEY = load_api_key()
BASE_URL = "https://apipri.stratus.ai/sapi"

ENDPOINTS = [
    ("getCommsHistory", "GET", {}),
    ("getWX", "GET", {"icao": "KLAX"}),
    ("getTFRs", "GET", {}),
    ("getVATSIM", "GET", {}),
    ("getParking", "GET", {}),
    ("startFlight", "GET", {}),
    ("startFlight", "POST", {"icao": "KLAX", "gate": "GATE 1"}),
    ("assignGate", "GET", {"icao": "KLAX", "gate": "GATE 1"}),
    ("setFreq", "GET", {"freq": "122.800", "channel": "COM1"}),
    ("setPause", "GET", {"pause": 1}),
]

def map_permissions():
    logger.info(f"Mapping permissions for Key: {API_KEY[:4]}...{API_KEY[-4:]}")
    
    for name, method, params in ENDPOINTS:
        params['api_key'] = API_KEY
        url = f"{BASE_URL}/{name}"
        try:
            if method == "GET":
                r = requests.get(url, params=params, timeout=5)
            else:
                r = requests.post(url, params={'api_key': API_KEY}, json=params, timeout=5)
            
            logger.info(f"{name.ljust(15)} | {method.ljust(4)} | {r.status_code} | {r.text[:100]}")
        except Exception as e:
            logger.error(f"{name.ljust(15)} | {method.ljust(4)} | ERR | {e}")

if __name__ == "__main__":
    map_permissions()
