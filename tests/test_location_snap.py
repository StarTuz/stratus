import requests
import json
import time
from pathlib import Path
import configparser

def test_location_snap():
    # Load config
    config = configparser.ConfigParser()
    config.read('config.init' if Path('config.init').exists() else 'config.ini')
    api_key = config.get('sapi', 'api_key', fallback=None)
    
    if not api_key:
        print("API Key not found")
        return

    # 1. First, set location to New York City (KJFK)
    print("--- SNAPPING TO NEW YORK CITY (KJFK) ---")
    lat_nyc = 40.6413
    lon_nyc = -73.7781
    
    # Use the corrected setVar parameters
    requests.get("https://apipri.stratus.ai/sapi/setVar", 
                 params={"api_key": api_key, "var": "PLANE LATITUDE", "value": str(lat_nyc)})
    requests.get("https://apipri.stratus.ai/sapi/setVar", 
                 params={"api_key": api_key, "var": "PLANE LONGITUDE", "value": str(lon_nyc)})
    
    # Send a heartbeat with NYC coords just in case
    hb_url = f"https://apipri.stratus.ai/sapi/v1/input?api_key={api_key}"
    hb_data = {
        "sim": {
            "variables": {
                "PLANE LATITUDE": lat_nyc,
                "PLANE LONGITUDE": lon_nyc,
                "PLANE ALTITUDE": 500,
                "INDICATED ALTITUDE": 500,
                "SIM ON GROUND": 1,
                "COM ACTIVE FREQUENCY:1": 119.100, # JFK Tower
                "TITLE": "NYC-SNAP-TEST",
                "ATC MODEL": "C172"
            }
        }
    }
    requests.post(hb_url, json=hb_data)
    
    print("Waiting 3 seconds for server to digest NYC...")
    time.sleep(3)
    
    print("Checking stations near KJFK...")
    resp = requests.get("https://apipri.stratus.ai/sapi/getCommsHistory", params={"api_key": api_key})
    # Note: History won't show stations unless we transmit, but we can check what it thinks our location is
    # by sending a 'Radio Check' message and seeing who responds.
    
    print("Sending Radio Check at KJFK (119.100)...")
    requests.get("https://apipri.stratus.ai/sapi/sayAs", 
                 params={"api_key": api_key, "message": "Kennedy Tower, Cessna 123AB Radio Check", "channel": "COM1"})
    
    time.sleep(5)
    resp = requests.get("https://apipri.stratus.ai/sapi/getCommsHistory", params={"api_key": api_key})
    history = resp.json()
    
    print(f"Full History Response: {json.dumps(history, indent=2)}")
    
    found_nyc = False
    if isinstance(history, list):
        for item in history:
            if not isinstance(item, dict): continue
            station = item.get("station_name", "")
            if "Kennedy" in station or "New York" in station:
                found_nyc = True
                print(f"SUCCESS! Found NYC station in history: {station}")
    
    if not found_nyc:
        print("FAILED: History still seems stuck or didn't update to NYC.")


if __name__ == "__main__":
    test_location_snap()
