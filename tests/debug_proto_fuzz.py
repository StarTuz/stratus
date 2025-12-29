
import requests
import json
import logging
import urllib.parse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

API_KEY = "s4GH8119xFyX"
HEADERS = {"X-API-Key": API_KEY}

# Payloads
TELEMETRY = {
   "sim" : {
      "variables" : {"PLANE LATITUDE": 34.0, "PLANE LONGITUDE": -118.0},
      "exe" : "example_sim_pro_v2.exe",
      "name" : "ExampleSimPro",
      "version" : "2.2.5.6",
      "adapter_version" : "0.9",
      "simapi_version" : "1.0"
   }
}

FLIGHT_JSON = {
  "flight_details": {
    "Email": "linux_user@example.com",
    "api_key": API_KEY,
    "callsign": "N123AB",
    "current_flight": {
      "flight_origin": "F70", 
      "flight_destination": "KLAX"
    }
  }
}

def test_endpoints():
    # 1. POST to startFlight
    logger.info("\n--- Test 1: POST flight.json to startFlight ---")
    try:
        url = "https://apipri.stratus.ai/sapi/startFlight"
        # Try as JSON
        r = requests.post(url, json=FLIGHT_JSON, headers=HEADERS, timeout=5)
        logger.info(f"JSON Result: {r.status_code} - {r.text}")
        
        # Try as Form
        r = requests.post(url, data=FLIGHT_JSON['flight_details'], headers=HEADERS, timeout=5)
        logger.info(f"Form Result: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"Error: {e}")

    # 2. Fuzz simapi/v1/input
    logger.info("\n--- Test 2: Fuzz simapi/v1/input ---")
    url = "https://apipri.stratus.ai/simapi/v1/input"
    
    # URL Encoded 'json'
    try:
        data = {"json": json.dumps(TELEMETRY), "api_key": API_KEY}
        r = requests.post(url, data=data, timeout=5)
        logger.info(f"'json' param Result: {r.status_code} - {r.text}")
    except Exception as e: pass

    # URL Encoded 'data'
    try:
        data = {"data": json.dumps(TELEMETRY), "api_key": API_KEY}
        r = requests.post(url, data=data, timeout=5)
        logger.info(f"'data' param Result: {r.status_code} - {r.text}")
    except Exception as e: pass
    
    # URL Encoded 'payload'
    try:
        data = {"payload": json.dumps(TELEMETRY), "api_key": API_KEY}
        r = requests.post(url, data=data, timeout=5)
        logger.info(f"'payload' param Result: {r.status_code} - {r.text}")
    except Exception as e: pass

    # URL Encoded 'simAPI_input.json'
    try:
        data = {"simAPI_input.json": json.dumps(TELEMETRY), "api_key": API_KEY}
        r = requests.post(url, data=data, timeout=5)
        logger.info(f"'simAPI_input.json' param Result: {r.status_code} - {r.text}")
    except Exception as e: pass
    
    # Query Param json
    try:
        json_str = urllib.parse.quote(json.dumps(TELEMETRY))
        r = requests.get(f"{url}?api_key={API_KEY}&json={json_str}", timeout=5)
        logger.info(f"GET with json param Result: {r.status_code} - {r.text}")
    except Exception as e: pass

    # 3. Multipart Fuzzing
    logger.info("\n--- Test 3: Multipart Fuzzing ---")
    try:
        # Multipart with 'json' key
        files = {'json': (None, json.dumps(TELEMETRY), 'application/json')}
        r = requests.post(url, files=files, params={'api_key': API_KEY}, timeout=5)
        logger.info(f"Multipart 'json' Result: {r.status_code} - {r.text}")
    except Exception as e: pass

    try:
        # Multipart with 'data' key
        files = {'data': (None, json.dumps(TELEMETRY), 'application/json')}
        r = requests.post(url, files=files, params={'api_key': API_KEY}, timeout=5)
        logger.info(f"Multipart 'data' Result: {r.status_code} - {r.text}")
    except Exception as e: pass

    # 4. flight.json to SimAPI
    logger.info("\n--- Test 4: flight.json to SimAPI ---")
    try:
        # Try sending flight details to simapi input
        data = {"json": json.dumps(FLIGHT_JSON), "api_key": API_KEY}
        r = requests.post(url, data=data, timeout=5)
        logger.info(f"flight.json as 'json' param Result: {r.status_code} - {r.text}")
    except Exception as e: pass

if __name__ == "__main__":
    test_endpoints()
