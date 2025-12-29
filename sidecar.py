#!/usr/bin/env python3
"""
Stratus Python Sidecar

Reads telemetry from the X-Plane plugin and forwards to the SAPI server.
This replaces the Windows sidecar for native Linux operation.
"""
import requests
import json
import logging
import time
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuration
TELEMETRY_FILE = Path.home() / ".local/share/StratusAI/simAPI_telemetry.json"
API_KEY = os.environ.get("SI_API_KEY", "s4GH8119xFyX")
USERNAME = os.environ.get("SI_USERNAME", "matt.g.johnson101@gmail.com")
PASSWORD = os.environ.get("SI_PASSWORD", "R%bbit9991!")
AUTH_URL = "https://lambda.stratus.ai/auth/login"
SAPI_URL = "https://apipri.stratus.ai/sapi/v1/input"
POLL_INTERVAL = 1.0  # seconds

class SapiSidecar:
    def __init__(self):
        self.token = None
        self.last_telemetry_time = 0
        
    def authenticate(self):
        """Login and get JWT token."""
        try:
            r = requests.post(AUTH_URL, json={
                "username": USERNAME,
                "password": PASSWORD
            }, timeout=10)
            data = r.json()
            self.token = data.get("token")
            if self.token:
                logger.info("✓ Authenticated successfully")
                return True
            else:
                logger.error(f"Auth failed: {data}")
                return False
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return False
    
    def read_telemetry(self):
        """Read telemetry from X-Plane plugin output."""
        try:
            if not TELEMETRY_FILE.exists():
                return None
            
            mtime = TELEMETRY_FILE.stat().st_mtime
            if mtime <= self.last_telemetry_time:
                return None  # File hasn't changed
            
            self.last_telemetry_time = mtime
            with open(TELEMETRY_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Telemetry read error: {e}")
            return None
    
    def convert_to_sapi_format(self, telemetry):
        """Convert X-Plane telemetry format to SAPI SimAPI format."""
        return {
            "name": "StratusML",
            "version": "1.0.0",
            "adapter_version": "1.0.0",
            "simapi_version": "1.0",
            "exe": "xplane12",
            "api_key": API_KEY,
            "variables": {
                "PLANE LATITUDE": telemetry.get("latitude", 0),
                "PLANE LONGITUDE": telemetry.get("longitude", 0),
                "PLANE ALTITUDE": telemetry.get("altitude_msl", 0),
                "PLANE HEADING DEGREES TRUE": telemetry.get("heading_true", 0),
                "PLANE HEADING DEGREES MAGNETIC": telemetry.get("heading_mag", 0),
                "SIM ON GROUND": 1 if telemetry.get("on_ground", False) else 0,
                "AIRSPEED INDICATED": telemetry.get("ias", 0),
                "VERTICAL SPEED": telemetry.get("vertical_speed", 0),
                "COM ACTIVE FREQUENCY:1": float(telemetry.get("com1", {}).get("active", "0").replace(".", "")),
                "COM STANDBY FREQUENCY:1": float(telemetry.get("com1", {}).get("standby", "0").replace(".", "")),
                "COM ACTIVE FREQUENCY:2": float(telemetry.get("com2", {}).get("active", "0").replace(".", "")),
                "TRANSPONDER CODE:1": telemetry.get("transponder", {}).get("code_int", 1200),
                "TITLE": telemetry.get("tail_number", "Unknown"),
                "LOCAL TIME": int(time.time()) % 86400,
                "ZULU TIME": int(time.time()) % 86400
            }
        }
    
    def send_telemetry(self, payload):
        """Send telemetry to SAPI server."""
        if not self.token:
            return False
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            r = requests.post(SAPI_URL, headers=headers, json=payload, timeout=5)
            if r.status_code == 200 and "Missing JSON" not in r.text:
                logger.info(f"✓ Telemetry sent: {r.status_code}")
                return True
            else:
                logger.warning(f"Telemetry response: {r.status_code} {r.text[:100]}")
                return False
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False
    
    def test_session(self):
        """Test if session is now active."""
        try:
            r = requests.get(
                "https://apipri.stratus.ai/sapi/assignGate",
                params={"api_key": API_KEY, "airport": "F70", "gate": "RAMP 1"},
                headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
                timeout=5
            )
            if "No active flight" not in r.text:
                logger.info(f"✓ SESSION ACTIVE! {r.text[:100]}")
                return True
            else:
                logger.debug("Session not active yet")
                return False
        except Exception as e:
            logger.error(f"Session test error: {e}")
            return False
    
    def run(self):
        """Main loop."""
        logger.info("Stratus Python Sidecar starting...")
        
        if not self.authenticate():
            logger.error("Failed to authenticate. Exiting.")
            return
        
        logger.info(f"Watching: {TELEMETRY_FILE}")
        logger.info("Sending telemetry every second...")
        
        send_count = 0
        while True:
            telemetry = self.read_telemetry()
            if telemetry:
                payload = self.convert_to_sapi_format(telemetry)
                self.send_telemetry(payload)
                send_count += 1
                
                # Test session every 10 sends
                if send_count % 10 == 0:
                    if self.test_session():
                        logger.info("🎉 Session is now ACTIVE!")
            
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    sidecar = SapiSidecar()
    try:
        sidecar.run()
    except KeyboardInterrupt:
        logger.info("Sidecar stopped.")
