#!/usr/bin/env python3
"""
X-Plane 12 Web API Test Script

Tests the REST API to read DataRefs directly from X-Plane.
No plugin required - X-Plane 12.1.1+ has this built-in.
"""

import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

API_BASE = "http://localhost:8086/api/v2"

def api_get(endpoint: str) -> Optional[Dict[str, Any]]:
    """Make a GET request to the X-Plane API."""
    url = f"{API_BASE}/{endpoint}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        return None


def find_dataref_id(name: str, all_datarefs: list) -> Optional[int]:
    """Find the ID for a dataref by name."""
    for dr in all_datarefs:
        if dr.get("name") == name:
            return dr.get("id")
    return None


def read_dataref_by_filter(name_pattern: str) -> None:
    """Read a dataref value using the filter parameter."""
    # The API supports filtering via query params
    result = api_get(f"datarefs?filter[name]={name_pattern}")
    if result:
        print(f"\nFiltered results for '{name_pattern}':")
        for dr in result.get("data", [])[:5]:
            print(f"  {dr.get('name')}: {dr.get('value', 'N/A')}")


def main():
    print("=" * 60)
    print("X-Plane 12 Web API Test")
    print("=" * 60)
    
    # Test 1: Check if API is accessible
    print("\n[1] Testing API connectivity...")
    result = api_get("datarefs")
    
    if not result:
        print("ERROR: Cannot connect to X-Plane Web API")
        print("Make sure X-Plane is running and Web API is enabled")
        return
    
    datarefs = result.get("data", [])
    print(f"SUCCESS: Found {len(datarefs)} DataRefs")
    
    # Test 2: Find specific datarefs we care about
    print("\n[2] Finding position DataRefs...")
    
    target_refs = [
        "sim/flightmodel/position/latitude",
        "sim/flightmodel/position/longitude", 
        "sim/flightmodel/position/elevation",
        "sim/flightmodel/position/mag_psi",
        "sim/flightmodel/position/indicated_airspeed",
        "sim/cockpit2/radios/actuators/com1_frequency_hz_833",
        "sim/cockpit/radios/transponder_code",
    ]
    
    found_refs = {}
    for target in target_refs:
        dr_id = find_dataref_id(target, datarefs)
        if dr_id:
            # Find the full object to get the value
            for dr in datarefs:
                if dr.get("name") == target:
                    found_refs[target] = dr
                    break
    
    print(f"Found {len(found_refs)}/{len(target_refs)} target DataRefs")
    
    # Test 3: Display current values
    print("\n[3] Current Aircraft State:")
    print("-" * 50)
    
    for name, dr in found_refs.items():
        short_name = name.split("/")[-1]
        value = dr.get("value", "N/A")
        
        # Format based on type
        if "latitude" in name or "longitude" in name:
            if value != "N/A":
                print(f"  {short_name:25}: {value:.6f}°")
            else:
                print(f"  {short_name:25}: {value}")
        elif "elevation" in name:
            if value != "N/A":
                print(f"  {short_name:25}: {value:.1f} m ({value * 3.28084:.0f} ft)")
            else:
                print(f"  {short_name:25}: {value}")
        elif "mag_psi" in name:
            if value != "N/A":
                print(f"  {short_name:25}: {value:.1f}°")
            else:
                print(f"  {short_name:25}: {value}")
        elif "airspeed" in name:
            if value != "N/A":
                print(f"  {short_name:25}: {value:.1f} kts")
            else:
                print(f"  {short_name:25}: {value}")
        elif "frequency" in name:
            if value != "N/A":
                freq_mhz = value / 1000 if value > 1000 else value
                print(f"  {short_name:25}: {freq_mhz:.3f} MHz")
            else:
                print(f"  {short_name:25}: {value}")
        elif "transponder" in name:
            if value != "N/A":
                print(f"  {short_name:25}: {int(value):04d}")
            else:
                print(f"  {short_name:25}: {value}")
        else:
            print(f"  {short_name:25}: {value}")
    
    # Test 4: Check if values are included in listing
    print("\n[4] API Value Inclusion Check:")
    sample = datarefs[0] if datarefs else {}
    print(f"  Sample DataRef keys: {list(sample.keys())}")
    
    if "value" not in sample:
        print("  NOTE: Values not included in listing. Need separate read calls.")
        print("  This is expected - X-Plane API requires individual reads.")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
