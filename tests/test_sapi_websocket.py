#!/usr/bin/env python3
"""
Stratus SAPI WebSocket Test

Tests WebSocket connectivity to the Stratus cloud.
"""

import asyncio
import configparser
import json
from pathlib import Path

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False


def load_config():
    """Load configuration from config.ini."""
    config = configparser.ConfigParser()
    config_path = Path(__file__).parent.parent / "config.ini"
    
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        return {}
    
    config.read(config_path)
    return {
        "api_key": config.get("sapi", "api_key", fallback=""),
        "api_url": config.get("sapi", "api_url", fallback="https://apipri.stratus.ai"),
    }


async def test_websocket():
    """Test WebSocket connection to SAPI."""
    print("=" * 60)
    print("Stratus SAPI WebSocket Test")
    print("=" * 60)
    
    if not HAS_WEBSOCKETS:
        print("\nERROR: websockets library not installed")
        print("Install with: pip install websockets")
        return
    
    config = load_config()
    if not config.get("api_key"):
        print("\nERROR: No API key configured")
        return
    
    api_key = config["api_key"]
    base_url = config["api_url"].replace("https://", "wss://").replace("http://", "ws://")
    
    # WebSocket endpoints to try
    ws_endpoints = [
        "/ws",
        "/api/ws", 
        "/api/v1/ws",
        "/socket",
    ]
    
    print(f"\n[1] Configuration")
    print(f"  Base URL: {base_url}")
    print(f"  API Key: {api_key[:4]}{'*' * (len(api_key)-4)}")
    
    for endpoint in ws_endpoints:
        ws_url = f"{base_url}{endpoint}"
        print(f"\n[2] Testing: {ws_url}")
        print("-" * 50)
        
        # Headers for authentication
        headers = {
            "X-API-Key": api_key,
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "StratusAIml/0.1.0 (Linux)",
        }
        
        try:
            async with websockets.connect(
                ws_url, 
                additional_headers=headers,
            ) as ws:
                print("  ✅ Connected!")
                
                # Try sending a hello/auth message
                auth_messages = [
                    {"type": "auth", "api_key": api_key},
                    {"type": "hello", "client": "StratusAIml", "version": "0.1.0"},
                    {"action": "connect", "key": api_key},
                ]
                
                for msg in auth_messages:
                    print(f"  → Sending: {json.dumps(msg)[:60]}...")
                    await ws.send(json.dumps(msg))
                    
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                        print(f"  ← Received: {response[:100]}")
                        
                        try:
                            data = json.loads(response)
                            print(f"  📦 Parsed: {json.dumps(data, indent=2)[:200]}")
                        except:
                            pass
                            
                    except asyncio.TimeoutError:
                        print("  ⏱️ No response (timeout)")
                    except Exception as e:
                        print(f"  ⚠️ Receive error: {e}")
                
                # Wait for any async messages
                print("\n  Listening for 5 seconds...")
                try:
                    while True:
                        response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        print(f"  ← Message: {response[:100]}")
                except asyncio.TimeoutError:
                    print("  ⏱️ No more messages")
                    
                return  # Success, stop trying other endpoints
                
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"  ❌ Rejected: HTTP {e.status_code}")
        except ConnectionRefusedError:
            print("  ❌ Connection refused")
        except Exception as e:
            print(f"  ❌ Error: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


def main():
    asyncio.run(test_websocket())


if __name__ == "__main__":
    main()
