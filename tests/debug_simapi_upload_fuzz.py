
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

API_KEY = "s4GH8119xFyX"
BASE_URL = "https://apipri.stratus.ai/simapi/v1/input"

PAYLOAD = {
   "sim" : {
      "variables" : {"PLANE LATITUDE": 34.0},
      "name" : "ExampleSimPro",
      "version" : "2.2.5.6"
   }
}

def test_upload_fuzz():
    logger.info(f"Target: {BASE_URL}")
    params = {"api_key": API_KEY}
    
    field_names = ["file", "upload", "json_file", "simapi_input", "simAPI_input", "input"]
    
    for name in field_names:
        logger.info(f"\n--- Testing field name: '{name}' ---")
        try:
            files = {
                name: ('simAPI_input.json', json.dumps(PAYLOAD), 'application/json')
            }
            r = requests.post(BASE_URL, params=params, files=files, timeout=10)
            logger.info(f"Result: {r.status_code} - {r.text}")
            logger.info(f"Cookies: {r.cookies.get_dict()}")
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    test_upload_fuzz()
