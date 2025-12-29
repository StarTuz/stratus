
import sys
import os
import time
import logging
from typing import Dict, Any

# Add client/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../client/src')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import SapiService
try:
    from core.sapi_interface import SapiService, Channel
except ImportError as e:
    logger.error(f"Import failed: {e}")
    sys.exit(1)

def main():
    logger.info("Starting Integration Test using SapiService...")
    
    sapi = SapiService()
    
    # 1. Connect
    if not sapi.connect():
        logger.error("Failed to connect! Check config.ini")
        sys.exit(1)
    
    logger.info("Connected to SAPI.")
    
    # 2. Start Flight
    logger.info("Calling startFlight...")
    try:
        # We access the session directly since start_flight isn't in SapiService yet
        url = f"{sapi.BASE_URL}/startFlight"
        params = {"api_key": sapi._api_key, "icao": "F70", "gate": "RAMP 1"}
        resp = sapi._session.get(url, params=params)
        logger.info(f"startFlight Result: {resp.status_code} - {resp.text}")
    except Exception as e:
        logger.error(f"startFlight failed: {e}")

    # 3. Telemetry Loop + Radio Check
    telemetry = {
        "latitude": 33.5799,
        "longitude": -117.1223,
        "altitude_msl": 1350.0,
        "altitude_agl": 0.0,
        "heading_mag": 100.0,
        "heading_true": 112.0,
        "pitch": 0.0,
        "roll": 0.0,
        "on_ground": True,
        "ias": 0.0,
        "groundspeed": 0.0,
        "vertical_speed": 0.0,
        "com1_active": "122.800",
        "com1_standby": "119.000",
        "com2_active": "121.500",
        "com2_standby": "121.500",
        "transponder_code": "1200",
        "transponder_mode": "ALT",
        "tail_number": "N123AB",
        "icao_type": "C172",
        "sim": "xplane",
        "timestamp": time.time()
    }

    logger.info("Sending telemetry loop...")
    for i in range(10):
        telemetry["timestamp"] = time.time()
        sapi.update_telemetry(telemetry)
        
        # Explicit vars
        sapi.set_variable("PLANE LATITUDE", f"{telemetry['latitude']:.6f}", "A")
        sapi.set_variable("PLANE LONGITUDE", f"{telemetry['longitude']:.6f}", "A")
        
        if i == 5:
            logger.info("Triggering Radio Check...")
            voice_resp = sapi.say_as("French Valley Traffic, N123AB radio check.", Channel.COM1)
            # We will rely on SapiService logging (which I'm about to add) to see the real error
            
        time.sleep(1)

if __name__ == "__main__":
    main()
