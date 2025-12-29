import requests
import json
import time
from pathlib import Path
import configparser

def test_f70_radio_check():
    # Load config
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_key = config.get('sapi', 'api_key', fallback=None)
    
    if not api_key:
        print("API Key not found")
        return

    # 1. Snap to French Valley (F70)
    print("--- SNAPPING TO FRENCH VALLEY (F70) ---")
    lat = 33.5750
    lon = -117.1281
    
    # Corrected setVar parameters
    requests.get("https://apipri.stratus.ai/sapi/setVar", 
                 params={"api_key": api_key, "var": "PLANE LATITUDE", "value": str(lat)})
    requests.get("https://apipri.stratus.ai/sapi/setVar", 
                 params={"api_key": api_key, "var": "PLANE LONGITUDE", "value": str(lon)})
    
    # Update frequency
    print("Setting frequency to 133.500...")
    requests.get("https://apipri.stratus.ai/sapi/setFreq", 
                 params={"api_key": api_key, "freq": "133.500", "channel": "COM1"})
    
    # 2. Heartbeat to sync
    hb_url = f"https://apipri.stratus.ai/sapi/v1/input?api_key={api_key}"
    hb_data = {
        "sim": {
            "variables": {
                "PLANE LATITUDE": lat,
                "PLANE LONGITUDE": lon,
                "PLANE ALTITUDE": 1345,
                "SIM ON GROUND": 1,
                "COM ACTIVE FREQUENCY:1": 133.5,
                "TITLE": "C-FIJM-F70-TEST",
                "ATC MODEL": "M7"
            },
            "name": "X-Plane 12 (Test)",
            "simapi_version": "1.0"
        }
    }
    requests.post(hb_url, json=hb_data)
    
    time.sleep(2)
    
    # 3. Send Transmission
    print("Sending Radio Check at French Valley...")
    resp = requests.get("https://apipri.stratus.ai/sapi/sayAs", 
                 params={
                     "api_key": api_key, 
                     "message": "French Valley Unicom, Cessna 123AB Radio Check", 
                     "channel": "COM1",
                     "entity": "atc"
                 })
    print(f"sayAs Status: {resp.status_code}")
    
    print("Waiting for response...")
    time.sleep(6)
    
    # 4. Check History with Coords
    print("Checking History with coords...")
    resp = requests.get("https://apipri.stratus.ai/sapi/getCommsHistory", 
                        params={"api_key": api_key, "lat": str(lat), "lon": str(lon)})
    history = resp.json()
    
    print(f"Found {len(history)} entries (or keys)")
    
    # Find NEW items
    new_found = False
    items = []
    if isinstance(history, dict):
        for k, v in history.items():
            if isinstance(v, list): items.extend(v)
    elif isinstance(history, list):
        items = history
        
    for item in items:
        station = item.get("station_name", "")
        msg = item.get("incoming_message", "")
        if "Valley" in station or "French" in station or "133.5" in str(item.get("frequency")):
            new_found = True
            print(f"!!! SUCCESS !!! FOUND FRENCH VALLEY ENTRY:")
            print(f"  Station: {station}")
            print(f"  Message: {msg}")
            print(f"  Frequency: {item.get('frequency')}")
    
    if not new_found:
        print("Still nothing from French Valley. History might be empty or stale.")

if __name__ == "__main__":
    test_f70_radio_check()
