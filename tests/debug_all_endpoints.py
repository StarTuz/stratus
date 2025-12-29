#!/usr/bin/env python3
"""
Test all possible telemetry endpoints to find one that works.
"""
import requests
import json
import os

USERNAME = os.environ.get("SI_USERNAME", "matt.g.johnson101@gmail.com")
PASSWORD = os.environ.get("SI_PASSWORD", "R%bbit9991!")
API_KEY = "s4GH8119xFyX"

def get_token():
    r = requests.post("https://lambda.stratus.ai/auth/login", 
                     json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    return r.json().get("token")

def test_all_endpoints():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    payload = {
        "name": "StratusML",
        "version": "1.0.0",
        "api_key": API_KEY,
        "variables": {
            "PLANE LATITUDE": 33.58,
            "PLANE LONGITUDE": -117.12,
            "PLANE ALTITUDE": 1345,
            "SIM ON GROUND": 1,
            "TITLE": "Cessna 172"
        }
    }
    
    endpoints = [
        "https://apipri.stratus.ai/sapi/v1/input",
        "https://apipri.stratus.ai/sapi/input",
        "https://apipri.stratus.ai/sapi/telemetry",
        "https://apipri.stratus.ai/sapi/startFlight",
        "https://apipri.stratus.ai/simapi/v1/input",
        "https://apipri.stratus.ai/api/v1/input",
        "https://lambda.stratus.ai/sapi/v1/input",
        "https://portal.stratus.ai/api/telemetry",
    ]
    
    for url in endpoints:
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=3)
            result = r.text[:80] if r.text else "(empty)"
            if "Missing JSON" not in result and r.status_code != 404:
                print(f"✓ {url.split('/')[-2:]}: {r.status_code} {result}")
            else:
                print(f"✗ {url.split('/')[-2:]}: {r.status_code} {result}")
        except Exception as e:
            print(f"✗ {url.split('/')[-2:]}: Error")
    
    # Check session
    print("\n--- Session Check ---")
    r = requests.get("https://apipri.stratus.ai/sapi/assignGate",
                    params={"api_key": API_KEY, "airport": "F70", "gate": "RAMP 1"},
                    headers=headers, timeout=5)
    print(f"assignGate: {r.text}")

if __name__ == "__main__":
    test_all_endpoints()
