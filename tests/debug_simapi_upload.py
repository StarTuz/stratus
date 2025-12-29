
import requests
import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

API_KEY = "s4GH8119xFyX"
BASE_URL = "https://apipri.stratus.ai/simapi/v1/input"

# Official Sample Payload (condensed)
PAYLOAD = {
   "sim" : {
      "variables" : {
         "PLANE LATITUDE" : 34.0,
         "PLANE LONGITUDE" : -118.0,
         "PLANE ALTITUDE" : 1000,
         "SIM ON GROUND" : 0,
         "AIRSPEED INDICATED" : 100
      },
      "exe" : "example_sim_pro_v2.exe",
      "name" : "ExampleSimPro",
      "version" : "2.2.5.6"
   }
}

def test_upload():
    logger.info(f"Target: {BASE_URL}")
    
    # 1. Test as Multipart File Upload (most likely for a 'file watcher')
    logger.info("\n--- Test 1: Multipart File Upload ---")
    try:
        files = {
            'simAPI_input.json': ('simAPI_input.json', json.dumps(PAYLOAD), 'application/json')
        }
        # Some servers need the key in the URL or form data
        params = {"api_key": API_KEY} 
        r = requests.post(BASE_URL, params=params, files=files, timeout=10)
        logger.info(f"Result: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"Error: {e}")

    # 2. Test as Form Data 'json' field
    logger.info("\n--- Test 2: Form Data 'json' field ---")
    try:
        data = {
            'api_key': API_KEY,
            'json': json.dumps(PAYLOAD)
        }
        r = requests.post(BASE_URL, data=data, timeout=10)
        logger.info(f"Result: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"Error: {e}")

    # 3. Test as Form Data 'data' field
    logger.info("\n--- Test 3: Form Data 'data' field ---")
    try:
        data = {
            'api_key': API_KEY,
            'data': json.dumps(PAYLOAD)
        }
        r = requests.post(BASE_URL, data=data, timeout=10)
        logger.info(f"Result: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    test_upload()
