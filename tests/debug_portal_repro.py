
import requests
import json
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Hardcoded from config.ini for repro stability
API_KEY = "s4GH8119xFyX"

# The official sample payload we just fetched
PAYLOAD = {
   "sim" : {
      "variables" : {
         "PLANE BANK DEGREES" : 0,
         "COM TRANSMIT:1" : 1,
         "INDICATED ALTITUDE" : 5902,
         "AIRSPEED TRUE" : 0,
         "TITLE" : "C172SP G1000 Cargo Livery: Cargo 02 Adaptive",
         "TOTAL WEIGHT" : 1898,
         "PLANE TOUCHDOWN LATITUDE" : 0,
         "PLANE ALTITUDE" : 5902,
         "WHEEL RPM:1" : 0,
         "ATC MODEL" : "ATCCOM.AC_MODEL C172.0.text",
         "COM TRANSMIT:2" : 0,
         "COM RECEIVE:2" : 0,
         "PLANE TOUCHDOWN NORMAL VELOCITY" : 0,
         "TRANSPONDER IDENT" : 0,
         "PLANE ALT ABOVE GROUND MINUS CG" : 0,
         "COM RECEIVE:1" : 1,
         "COM STANDBY FREQUENCY:1" : 119.99,
         "INTERCOM SYSTEM ACTIVE" : 0,
         "AIRSPEED INDICATED" : 0,
         "SEA LEVEL PRESSURE" : 1013,
         "PLANE LONGITUDE" : -120.132249773466,
         "ENGINE TYPE" : 0,
         "LOCAL TIME" : 60863.319,
         "PLANE PITCH DEGREES" : 0,
         "COM ACTIVE FREQUENCY:2" : 121.5,
         "CIRCUIT COM ON:1" : 1,
         "COM STANDBY FREQUENCY:2" : 124.85,
         "TRANSPONDER STATE:1" : 4,
         "TRANSPONDER CODE:1" : 1200,
         "PLANE HEADING DEGREES TRUE" : 5,
         "MAGNETIC COMPASS" : 287,
         "COM ACTIVE FREQUENCY:1" : 127.95,
         "VERTICAL SPEED" : 0,
         "ELECTRICAL MASTER BATTERY:0" : 1,
         "PLANE TOUCHDOWN LONGITUDE" : 0,
         "WHEEL RPM:0" : 0,
         "AUDIO PANEL VOLUME" : 75,
         "COM VOLUME:1" : 46,
         "SIM ON GROUND" : 1,
         "ZULU TIME" : 86063.319,
         "PLANE LATITUDE" : 39.3156749179636,
         "TYPICAL DESCENT RATE" : 1000,
         "AMBIENT WIND VELOCITY" : 0,
         "AMBIENT WIND DIRECTION" : 270,
         "COM VOLUME:2" : 81,
         "CIRCUIT COM ON:2" : 1,
         "WING SPAN" : 36,
         "ZULU DAY OF YEAR" : 84,
         "MAGVAR" : 12
      },
      "exe" : "example_sim_pro_v2.exe",
      "simapi_version" : "1.0",
      "name" : "ExampleSimPro",
      "version" : "2.2.5.6",
      "adapter_version" : "0.9"
   }
}

def test_endpoints():
    endpoints = [
        ("https://apipri.stratus.ai/sapi/v1/input", "POST"),
        ("https://apipri.stratus.ai/simapi/v1/input", "POST"),
    ]
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }

    print(f"Testing with payload size: {len(json.dumps(PAYLOAD))} bytes")
    
    for url, method in endpoints:
        print(f"\nTesting {url}...")
        try:
            # Try with query param too
            full_url = f"{url}?api_key={API_KEY}"
            r = requests.post(full_url, json=PAYLOAD, headers=headers, timeout=5)
            print(f"Status: {r.status_code}")
            print(f"Body: {r.text}")
            
            # If success, try to assign gate immediately to see if session formed
            if r.status_code == 200 and "Missing JSON" not in r.text:
                 gate_url = "https://apipri.stratus.ai/sapi/assignGate"
                 gate_r = requests.get(gate_url, params={"api_key": API_KEY, "gate": "A1", "airport": "KTRK"})
                 print(f"Gate Assign Check: {gate_r.text}")
                 
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_endpoints()
