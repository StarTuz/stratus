#!/usr/bin/env python3
"""
Continuous telemetry sender - runs for 60 seconds to test if sustained data creates a session.
"""
import requests
import json
import time
import os
from pathlib import Path

USERNAME = os.environ.get("SI_USERNAME", "matt.g.johnson101@gmail.com")
PASSWORD = os.environ.get("SI_PASSWORD", "R%bbit9991!")
API_KEY = "s4GH8119xFyX"
TELEMETRY_FILE = Path.home() / ".local/share/StratusAI/simAPI_telemetry.json"

def get_token():
    r = requests.post("https://lambda.stratus.ai/auth/login", 
                     json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    return r.json().get("token")

def read_telemetry():
    try:
        with open(TELEMETRY_FILE) as f:
            return json.load(f)
    except:
        return None

def main():
    token = get_token()
    print(f"✓ Authenticated")
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Send to multiple endpoints
    endpoints = [
        "https://apipri.stratus.ai/sapi/v1/input",
        "https://apipri.stratus.ai/sapi/input",
    ]
    
    print("Sending continuous telemetry for 60 seconds...")
    start_time = time.time()
    count = 0
    session_active = False
    
    while time.time() - start_time < 60:
        telemetry = read_telemetry()
        if not telemetry:
            time.sleep(1)
            continue
        
        # Convert to SAPI format
        payload = {
            "name": "StratusML",
            "version": "1.0.0",
            "api_key": API_KEY,
            "variables": {
                "PLANE LATITUDE": telemetry.get("latitude", 0),
                "PLANE LONGITUDE": telemetry.get("longitude", 0),
                "PLANE ALTITUDE": telemetry.get("altitude_msl", 0),
                "PLANE HEADING DEGREES TRUE": telemetry.get("heading_true", 0),
                "SIM ON GROUND": 1 if telemetry.get("on_ground") else 0,
                "AIRSPEED INDICATED": telemetry.get("ias", 0),
                "COM ACTIVE FREQUENCY:1": telemetry.get("com1", {}).get("active_hz", 121900),
                "TRANSPONDER CODE:1": telemetry.get("transponder", {}).get("code_int", 1200),
                "LOCAL TIME": int(time.time()) % 86400,
                "ZULU TIME": int(time.time()) % 86400
            }
        }
        
        # Send to all endpoints
        for url in endpoints:
            try:
                requests.post(url, headers=headers, json=payload, timeout=2)
            except:
                pass
        
        count += 1
        elapsed = int(time.time() - start_time)
        
        # Check session every 10 seconds
        if count % 10 == 0:
            try:
                r = requests.get("https://apipri.stratus.ai/sapi/assignGate",
                                params={"api_key": API_KEY, "airport": "F70", "gate": "RAMP 1"},
                                headers=headers, timeout=3)
                if "No active flight" not in r.text:
                    print(f"\n🎉 SESSION ACTIVE at {elapsed}s! Response: {r.text[:100]}")
                    session_active = True
                    break
                else:
                    print(f"[{elapsed}s] Sent {count} packets, session still inactive...")
            except:
                pass
        
        time.sleep(1)
    
    # Final check
    print("\n--- Final Session Check ---")
    r = requests.get("https://apipri.stratus.ai/sapi/assignGate",
                    params={"api_key": API_KEY, "airport": "F70", "gate": "RAMP 1"},
                    headers=headers, timeout=5)
    print(f"assignGate: {r.text}")
    
    if session_active:
        print("\n✓ SUCCESS! Session was established!")
    else:
        print("\n✗ Session was NOT established after 60 seconds of telemetry")

if __name__ == "__main__":
    main()
