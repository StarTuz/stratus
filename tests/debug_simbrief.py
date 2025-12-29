#!/usr/bin/env python3
"""
Test SimBrief integration to pre-load a session.
"""
import requests
import os

USERNAME = os.environ.get("SI_USERNAME", "matt.g.johnson101@gmail.com")
PASSWORD = os.environ.get("SI_PASSWORD", "R%bbit9991!")
API_KEY = "s4GH8119xFyX"

def get_token():
    r = requests.post("https://lambda.stratus.ai/auth/login", 
                     json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    return r.json().get("token")

def test_simbrief():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Try various SimBrief endpoints
    endpoints = [
        ("GET", "https://portal.stratus.ai/api/simbrief", {}),
        ("GET", "https://portal.stratus.ai/api/flightplan", {}),
        ("GET", "https://lambda.stratus.ai/getFlightPlan", {}),
        ("POST", "https://portal.stratus.ai/api/simbrief/load", {"pilot_id": "842506"}),
        ("POST", "https://portal.stratus.ai/api/efb/submitFlightPlan", {
            "origin": "F70",
            "destination": "KLAX",
            "cruiseAltitude": 5500
        }),
    ]
    
    for method, url, body in endpoints:
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=3)
            else:
                r = requests.post(url, headers=headers, json=body, timeout=3)
            
            result = r.text[:100] if r.text else "(empty)"
            print(f"{method} {url.split('/')[-1]}: {r.status_code} {result}")
        except Exception as e:
            print(f"{method} {url.split('/')[-1]}: Error {str(e)[:30]}")
    
    # Check session
    print("\n--- Session Check ---")
    r = requests.get("https://apipri.stratus.ai/sapi/assignGate",
                    params={"api_key": API_KEY, "airport": "F70", "gate": "RAMP 1"},
                    headers=headers, timeout=5)
    print(f"assignGate: {r.text}")

if __name__ == "__main__":
    test_simbrief()
