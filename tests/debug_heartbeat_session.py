#!/usr/bin/env python3
"""
Test the session heartbeat + Radio Check sequence.
Based on documentation: exe field + 1/sec updates + Radio Check = session
"""
import requests
import json
import time
import os
from pathlib import Path

API_KEY = "s4GH8119xFyX"
USERNAME = os.environ.get("SI_USERNAME", "matt.g.johnson101@gmail.com") 
PASSWORD = os.environ.get("SI_PASSWORD", "R%bbit9991!")
SIMAPI_FILE = Path.home() / ".local/share/StratusAI/simAPI_input.json"

def get_token():
    r = requests.post("https://lambda.stratus.ai/auth/login", 
                     json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    return r.json().get("token")

def write_simapi_with_exe():
    """Write simAPI_input.json with the exe field as documented."""
    data = {
        "sim": {
            "variables": {
                "PLANE_LATITUDE": 33.58,
                "PLANE_LONGITUDE": -117.12,
                "PLANE_ALTITUDE": 1345,
                "GROUND_SPEED": 0,
                "COM_ACTIVE_FREQUENCY:1": 133.5,
                "SIM_ON_GROUND": 1,
                "exe": "xplane12.exe"  # THE MISSING FIELD!
            }
        },
        "name": "StratusML_Linux",
        "simapi_version": "1.0"
    }
    with open(SIMAPI_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    return data

def radio_check(token):
    """Perform the Radio Check to lock in the session."""
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(
        "https://apipri.stratus.ai/sapi/sayAs",
        params={
            "api_key": API_KEY,
            "channel": "COM1",
            "message": "Radio check"
        },
        headers=headers,
        timeout=10
    )
    return r.status_code, r.text

def check_session(token):
    """Check if session is now active."""
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(
        "https://apipri.stratus.ai/sapi/assignGate",
        params={"api_key": API_KEY, "airport": "F70", "gate": "RAMP 1"},
        headers=headers,
        timeout=5
    )
    return "No active flight" not in r.text, r.text

def main():
    print("=== Session Heartbeat + Radio Check Test ===\n")
    
    # Step 1: Authenticate
    token = get_token()
    print(f"✓ Authenticated")
    
    # Step 2: Write simAPI_input.json with exe field
    print(f"\n1. Writing simAPI_input.json with 'exe' field...")
    data = write_simapi_with_exe()
    print(f"   Written: {SIMAPI_FILE}")
    print(f"   exe field: {data['sim']['variables']['exe']}")
    
    # Step 3: Simulate heartbeat (update file every second for 5 seconds)
    print(f"\n2. Simulating heartbeat (5 seconds)...")
    for i in range(5):
        write_simapi_with_exe()
        print(f"   Heartbeat {i+1}/5")
        time.sleep(1)
    
    # Step 4: Radio Check
    print(f"\n3. Calling sayAs with 'Radio check'...")
    status, response = radio_check(token)
    print(f"   Status: {status}")
    print(f"   Response: {response[:200]}")
    
    # Step 5: Check if session is active
    print(f"\n4. Checking session status...")
    active, response = check_session(token)
    if active:
        print(f"   🎉 SESSION ACTIVE! Response: {response[:200]}")
    else:
        print(f"   ❌ Still no session: {response[:100]}")
    
    # Step 6: Try with more heartbeats + another radio check
    if not active:
        print(f"\n5. Trying 10 more heartbeats + Radio Check...")
        for i in range(10):
            write_simapi_with_exe()
            time.sleep(1)
        status, response = radio_check(token)
        print(f"   sayAs: {status} {response[:100]}")
        
        active, response = check_session(token)
        if active:
            print(f"   🎉 SESSION ACTIVE! Response: {response[:200]}")
        else:
            print(f"   ❌ Still no session: {response[:100]}")

if __name__ == "__main__":
    main()
