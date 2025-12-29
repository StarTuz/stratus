#!/usr/bin/env python3
"""
Stratus SAPI API Test

Tests connectivity to the Stratus cloud API.
"""

import configparser
import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any


def load_config() -> Dict[str, str]:
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


def api_request(url: str, api_key: str, method: str = "GET", 
                data: Optional[Dict] = None) -> tuple:
    """Make an API request and return (status_code, response_data)."""
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("X-API-Key", api_key)
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "StratusAIml/0.1.0 (Linux)")
    
    if data:
        req.data = json.dumps(data).encode("utf-8")
    
    req.method = method
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()
        except:
            pass
        return e.code, body
    except urllib.error.URLError as e:
        return 0, str(e.reason)
    except Exception as e:
        return 0, str(e)


def main():
    print("=" * 60)
    print("Stratus SAPI API Test")
    print("=" * 60)
    
    # Load config
    config = load_config()
    if not config.get("api_key"):
        print("\nERROR: No API key configured")
        return
    
    api_key = config["api_key"]
    base_url = config["api_url"]
    
    print(f"\n[1] Configuration")
    print(f"  API URL: {base_url}")
    print(f"  API Key: {api_key[:4]}{'*' * (len(api_key)-4)}")
    
    # Test endpoints
    print(f"\n[2] Testing API Endpoints")
    print("-" * 50)
    
    # Common endpoints to try
    endpoints = [
        ("GET", "/", "Root"),
        ("GET", "/api", "API Info"),
        ("GET", "/api/v1", "API v1"),
        ("GET", "/api/v1/status", "Status"),
        ("GET", "/api/v1/health", "Health"),
        ("GET", "/api/v1/user", "User Info"),
        ("GET", "/api/v1/profile", "Profile"),
        ("GET", "/api/v1/session", "Session"),
        ("POST", "/api/v1/auth", "Auth"),
        ("GET", "/v1/status", "Alt Status"),
        ("GET", "/status", "Simple Status"),
        ("GET", "/health", "Simple Health"),
    ]
    
    for method, path, name in endpoints:
        url = f"{base_url}{path}"
        status, body = api_request(url, api_key, method)
        
        if status == 200:
            print(f"  ✅ {name:15} ({method} {path}): OK")
            if body:
                try:
                    data = json.loads(body)
                    for key, value in list(data.items())[:3]:
                        print(f"      {key}: {str(value)[:50]}")
                except:
                    print(f"      {body[:100]}")
        elif status == 401:
            print(f"  🔐 {name:15} ({method} {path}): Unauthorized (401)")
        elif status == 403:
            print(f"  🚫 {name:15} ({method} {path}): Forbidden (403)")
        elif status == 404:
            print(f"  ❌ {name:15} ({method} {path}): Not Found (404)")
        elif status == 0:
            print(f"  ⚠️  {name:15} ({method} {path}): {body[:50]}")
        else:
            print(f"  ❓ {name:15} ({method} {path}): HTTP {status}")
    
    # Try WebSocket endpoint discovery
    print(f"\n[3] WebSocket Endpoint Discovery")
    print("-" * 50)
    
    ws_endpoints = [
        "/ws",
        "/api/ws",
        "/api/v1/ws",
        "/socket",
        "/api/socket",
        "/stream",
        "/api/stream",
    ]
    
    for path in ws_endpoints:
        url = f"{base_url}{path}"
        status, body = api_request(url, api_key)
        if status != 404:
            print(f"  Found: {path} (HTTP {status})")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
