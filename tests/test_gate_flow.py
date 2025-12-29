
import requests
import time
import json

API_KEY = "s4GH8119xFyX"
# Trying /simapi/v1/input instead of /sapi/v1/input
BASE_TELEMETRY_URL = "https://apipri.stratus.ai/simapi"
BASE_SAPI_URL = "https://apipri.stratus.ai/sapi"

def start_flight():
    url = f"{BASE_SAPI_URL}/startFlight"
    params = {"api_key": API_KEY}
    print(f"Starting flight...")
    r = requests.get(url, params=params)
    print(f"Response: {r.status_code} {r.text}")

def send_telemetry():
    url = f"{BASE_TELEMETRY_URL}/v1/input"
    # Note: query param for api_key here
    params = {"api_key": API_KEY}
    headers = {
        "Content-Type": "application/json"
    }
    now = time.time()
    data = {
        "sim": {
            "variables": {
                "PLANE LATITUDE": 33.593,
                "PLANE LONGITUDE": -117.130,
                "PLANE ALTITUDE": 1100,
                "INDICATED ALTITUDE": 1100,
                "SIM ON GROUND": 1,
                "COM ACTIVE FREQUENCY:1": 123.500,
                "COM STANDBY FREQUENCY:1": 118.000,
                "TRANSPONDER CODE:1": 1200,
                "TRANSPONDER STATE:1": 4,
                "LOCAL TIME": now % 86400,
                "ZULU TIME": now % 86400,
                "TITLE": "N123456",
                "ATC MODEL": "C172"
            },
            "exe": "msfs.exe",
            "simapi_version": "1.0",
            "name": "MSFS"
        }
    }
    print(f"Sending telemetry to {url}...")
    r = requests.post(url, json=data, params=params, headers=headers)
    print(f"Response: {r.status_code} {r.text}")

def assign_gate(icao, gate):
    url = f"{BASE_SAPI_URL}/assignGate"
    params = {
        "api_key": API_KEY,
        "icao": icao,
        "gate": gate
    }
    print(f"Assigning gate at {icao}...")
    r = requests.get(url, params=params)
    print(f"Response: {r.status_code} {r.text}")

if __name__ == "__main__":
    start_flight()
    for i in range(5):
        send_telemetry()
        time.sleep(1)
    
    assign_gate("F70", "RAMP 1")
