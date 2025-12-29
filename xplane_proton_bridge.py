#!/usr/bin/env python3
"""
Write simAPI_input.json in EXACT DCS adapter format to Proton prefix.
Run this continuously while the Windows client is running.
"""
import json
import time
import os
from pathlib import Path

# Proton prefix path (where Windows client expects the file)
PROTON_LOCALAPPDATA = Path("/home/startux/.steam/steam/steamapps/compatdata/3062906073/pfx/drive_c/users/steamuser/AppData/Local/StratusAI")

# Also Linux path (where X-Plane plugin writes)
LINUX_TELEMETRY = Path.home() / ".local/share/StratusAI/simAPI_telemetry.json"

SIMAPI_INPUT_FILE = PROTON_LOCALAPPDATA / "simAPI_input.json"

def read_xplane_telemetry():
    """Read current telemetry from X-Plane plugin."""
    try:
        with open(LINUX_TELEMETRY) as f:
            return json.load(f)
    except:
        return None

def convert_to_dcs_format(xp_data):
    """Convert X-Plane telemetry to exact DCS/SimAPI format."""
    # Get COM frequencies in MHz format (without decimal point in Hz)
    com1_mhz = float(xp_data.get("com1", {}).get("active", "121.5").replace(".", "")) / 1000
    com2_mhz = float(xp_data.get("com2", {}).get("active", "121.5").replace(".", "")) / 1000
    com1_stby = float(xp_data.get("com1", {}).get("standby", "121.5").replace(".", "")) / 1000
    com2_stby = float(xp_data.get("com2", {}).get("standby", "121.5").replace(".", "")) / 1000
    
    return {
        "sim": {
            "name": "XPlane",
            "version": "X-Plane 12.1.2",
            "adapter_version": "XPLANE_LINUX_V1.0",
            "simapi_version": "v1",
            "exe": "X-Plane.exe",  # Windows client checks for running .exe
            "variables": {
                "PLANE LATITUDE": xp_data.get("latitude", 0),
                "PLANE LONGITUDE": xp_data.get("longitude", 0),
                "PLANE ALTITUDE": xp_data.get("altitude_msl", 0),
                "INDICATED ALTITUDE": xp_data.get("altitude_msl", 0),
                "PLANE HEADING DEGREES TRUE": xp_data.get("heading_true", 0),
                "MAGNETIC COMPASS": xp_data.get("heading_mag", 0),
                "PLANE PITCH DEGREES": xp_data.get("pitch", 0),
                "PLANE BANK DEGREES": xp_data.get("roll", 0),
                "SIM ON GROUND": 1 if xp_data.get("on_ground", True) else 0,
                "AIRSPEED INDICATED": xp_data.get("ias", 0),
                "AIRSPEED TRUE": xp_data.get("tas", 0) if isinstance(xp_data.get("tas"), (int, float)) else 0,
                "VERTICAL SPEED": xp_data.get("vertical_speed", 0),
                "COM ACTIVE FREQUENCY:1": com1_mhz,
                "COM STANDBY FREQUENCY:1": com1_stby,
                "COM ACTIVE FREQUENCY:2": com2_mhz,
                "COM STANDBY FREQUENCY:2": com2_stby,
                "COM TRANSMIT:1": 1,
                "COM TRANSMIT:2": 0,
                "COM RECEIVE:1": 1,
                "COM RECEIVE:2": 0,
                "CIRCUIT COM ON:1": 1,
                "CIRCUIT COM ON:2": 1,
                "TRANSPONDER CODE:1": xp_data.get("transponder", {}).get("code_int", 1200),
                "TRANSPONDER STATE:1": xp_data.get("transponder", {}).get("mode_int", 0),
                "TRANSPONDER IDENT": 0,
                "ELECTRICAL MASTER BATTERY:0": 1,
                "ENGINE TYPE": 0,  # 0 = Piston
                "TYPICAL DESCENT RATE": 500,
                "LOCAL TIME": int(time.time()) % 86400,
                "ZULU TIME": int(time.time()) % 86400,
                "TITLE": xp_data.get("tail_number", "N12345"),
                "TOTAL WEIGHT": 2500,
            }
        }
    }

def main():
    print("=== X-Plane to Proton SimAPI Bridge ===")
    print(f"Reading from: {LINUX_TELEMETRY}")
    print(f"Writing to: {SIMAPI_INPUT_FILE}")
    print("Press Ctrl+C to stop\n")
    
    # Ensure directory exists
    PROTON_LOCALAPPDATA.mkdir(parents=True, exist_ok=True)
    
    count = 0
    while True:
        xp_data = read_xplane_telemetry()
        if xp_data:
            simapi_data = convert_to_dcs_format(xp_data)
            with open(SIMAPI_INPUT_FILE, 'w') as f:
                json.dump(simapi_data, f, indent=4)
            count += 1
            if count % 10 == 0:
                print(f"[{count}] Written: Lat {xp_data.get('latitude', 0):.4f}, Lon {xp_data.get('longitude', 0):.4f}")
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBridge stopped.")
