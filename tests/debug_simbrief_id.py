#!/usr/bin/env python3
"""
Test SimBrief integration with user's actual SimBrief ID.
"""
import requests
import os

USERNAME = os.environ.get("SI_USERNAME", "matt.g.johnson101@gmail.com")
PASSWORD = os.environ.get("SI_PASSWORD", "R%bbit9991!")
API_KEY = "s4GH8119xFyX"
SIMBRIEF_ID = "65460"  # User's SimBrief UserID

def get_token():
    r = requests.post("https://lambda.stratus.ai/auth/login", 
                     json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    return r.json().get("token")

def test_simbrief_with_id():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    print("Testing SimBrief with UserID 65460...")
    
    # Try submitting a flight plan with SimBrief ID
    endpoints = [
        ("POST", "https://portal.stratus.ai/api/efb/submitFlightPlan", {
            "origin": "F70",
            "destination": "KLAX",
            "cruiseAltitude": 5500,
            "simbrief_id": SIMBRIEF_ID,
            "pilot_id": SIMBRIEF_ID
        }),
        ("GET", f"https://apipri.stratus.ai/sapi/getFlightPlan?api_key={API_KEY}&simbrief_id={SIMBRIEF_ID}", None),
        ("POST", "https://apipri.stratus.ai/sapi/startFlight", {
            "api_key": API_KEY,
            "simbrief_id": SIMBRIEF_ID,
            "origin": "F70"
        }),
    ]
    
    for method, url, body in endpoints:
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=5)
            else:
                r = requests.post(url, headers=headers, json=body, timeout=5)
            
            result = r.text[:150] if r.text else "(empty)"
            short_url = url.split("?")[0].split("/")[-1]
            print(f"{method} {short_url}: {r.status_code} {result}")
        except Exception as e:
            print(f"Error: {e}")
    
    # Check session
    print("\n--- Session Check ---")
    r = requests.get("https://apipri.stratus.ai/sapi/assignGate",
                    params={"api_key": API_KEY, "airport": "F70", "gate": "RAMP 1"},
                    headers=headers, timeout=5)
    print(f"assignGate: {r.text}")

if __name__ == "__main__":
    test_simbrief_with_id()
