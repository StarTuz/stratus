#!/usr/bin/env python3
"""
Test WebSocket connection to Comlink for session establishment.
"""
import asyncio
import json
import os
import websockets
import requests

USERNAME = os.environ.get("SI_USERNAME", "matt.g.johnson101@gmail.com")
PASSWORD = os.environ.get("SI_PASSWORD", "R%bbit9991!")
API_KEY = "s4GH8119xFyX"

def get_token():
    r = requests.post("https://lambda.stratus.ai/auth/login", 
                     json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    return r.json().get("token")

async def test_websocket():
    token = get_token()
    print(f"Got token: {token[:20]}...")
    
    # Try different WebSocket endpoints
    ws_urls = [
        f"wss://lambda.stratus.ai/comlink?type=simconnect&token={token}",
        f"wss://lambda.stratus.ai/comlink?type=efb&token={token}",
        f"wss://comlink.stratus.ai/?token={token}",
        f"wss://apipri.stratus.ai/ws?token={token}",
    ]
    
    for url in ws_urls:
        short_url = url.split("?")[0]
        print(f"\nTrying: {short_url}...")
        try:
            headers = {"Authorization": f"Bearer {token}"}
            async with websockets.connect(url, additional_headers=headers, close_timeout=3) as ws:
                print(f"  ✓ Connected!")
                
                # Send initial telemetry
                telemetry = {
                    "type": "telemetry",
                    "api_key": API_KEY,
                    "latitude": 33.58,
                    "longitude": -117.12,
                    "altitude": 1345,
                    "on_ground": True,
                    "com1_active": "133.500"
                }
                await ws.send(json.dumps(telemetry))
                print(f"  Sent telemetry")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=3)
                    print(f"  Response: {response[:200]}")
                except asyncio.TimeoutError:
                    print(f"  No response within 3s")
                except Exception as e:
                    print(f"  Recv error: {e}")
                    
        except Exception as e:
            print(f"  ✗ Failed: {str(e)[:60]}")
    
    # Check session after all attempts
    print("\n--- Session Check ---")
    r = requests.get("https://apipri.stratus.ai/sapi/assignGate",
                    params={"api_key": API_KEY, "airport": "F70", "gate": "RAMP 1"},
                    headers={"Authorization": f"Bearer {token}"}, timeout=5)
    print(f"assignGate: {r.text}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
