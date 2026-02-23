#!/usr/bin/env python3
"""
X-Plane 12 WebSocket API Test

Tests the WebSocket API for real-time DataRef subscriptions.
"""

import asyncio
import json

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

WEBSOCKET_URL = "ws://localhost:8086/api/v2/websocket"


async def test_websocket():
    """Test WebSocket connection and DataRef subscription."""
    print("=" * 60)
    print("X-Plane 12 WebSocket API Test")
    print("=" * 60)
    
    if not HAS_WEBSOCKETS:
        print("\nERROR: websockets library not installed")
        print("Install with: pip install websockets")
        return
    
    print(f"\n[1] Connecting to {WEBSOCKET_URL}...")
    
    try:
        async with websockets.connect(WEBSOCKET_URL, ping_timeout=10) as ws:
            print("SUCCESS: Connected!")
            
            # Subscribe to position datarefs
            print("\n[2] Subscribing to DataRefs...")
            
            subscribe_msg = {
                "req_id": 1,
                "type": "dataref_subscribe",
                "params": {
                    "datarefs": [
                        {"name": "sim/flightmodel/position/latitude"},
                        {"name": "sim/flightmodel/position/longitude"},
                        {"name": "sim/flightmodel/position/elevation"},
                        {"name": "sim/flightmodel/position/mag_psi"},
                        {"name": "sim/flightmodel/position/indicated_airspeed"},
                        {"name": "sim/cockpit2/radios/actuators/com1_frequency_hz_833"},
                        {"name": "sim/cockpit/radios/transponder_code"},
                    ]
                }
            }
            
            await ws.send(json.dumps(subscribe_msg))
            print("Sent subscription request")
            
            # Wait for responses
            print("\n[3] Receiving data (5 seconds)...")
            print("-" * 50)
            
            received_values = {}
            start_time = asyncio.get_event_loop().time()
            
            try:
                while (asyncio.get_event_loop().time() - start_time) < 5:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        data = json.loads(msg)
                        
                        if data.get("type") == "dataref_value":
                            name = data.get("name", "unknown")
                            value = data.get("value")
                            short_name = name.split("/")[-1]
                            received_values[short_name] = value
                            print(f"  {short_name}: {value}")
                        elif data.get("type") == "result":
                            print(f"  [Result] success={data.get('success')}")
                        else:
                            print(f"  [Other] {data.get('type', 'unknown')}: {str(data)[:100]}")
                            
                    except asyncio.TimeoutError:
                        continue
                        
            except Exception as e:
                print(f"Error receiving: {e}")
            
            print("-" * 50)
            print(f"\n[4] Summary: Received {len(received_values)} unique values")
            
            for name, value in received_values.items():
                print(f"  {name}: {value}")
                
    except ConnectionRefusedError:
        print("ERROR: Connection refused. Is X-Plane running?")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


def main():
    """Run the async test."""
    asyncio.run(test_websocket())


if __name__ == "__main__":
    main()
