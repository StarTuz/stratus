
import requests
import configparser
import time
import json
import logging
from threading import Thread, Event

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_api_key():
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_key = config.get('sapi', 'api_key', fallback=None)
    if not api_key:
        logger.error("API Key not found in config.ini")
        exit(1)
    return api_key

class TelemetrySender(Thread):
    def __init__(self, api_key, lat, lon, alt, hdg):
        super().__init__()
        self.api_key = api_key
        self.lat = lat
        self.lon = lon
        self.alt = alt
        self.hdg = hdg
        self.stop_event = Event()
        self.daemon = True

    def run(self):
        # Using SAPI endpoint, which returns 200 OK
        url = f"https://apipri.stratus.ai/sapi/v1/input?api_key={self.api_key}"
        
        while not self.stop_event.is_set():
            data = {
                "sim": {
                    "variables": {
                        "PLANE LATITUDE": f"{self.lat:.6f}",
                        "PLANE LONGITUDE": f"{self.lon:.6f}",
                        "PLANE ALTITUDE": self.alt,
                        "INDICATED ALTITUDE": self.alt,
                        "SIM ON GROUND": 1,
                        "PLANE HEADING DEGREES TRUE": self.hdg,
                        "OnGround": 1, 
                        "LOCAL TIME": time.time() % 86400,
                        "ZULU TIME": time.time() % 86400,
                        "TITLE": "C172", 
                        "ATC MODEL": "C172",
                        "COM ACTIVE FREQUENCY:1": 122.800, # F70 CTAF
                        "COM TRANSMIT:1": 1,
                        "COM RECEIVE:1": 1,
                        "ELECTRICAL MASTER BATTERY:0": 1,
                        "AIRSPEED INDICATED": 0,
                        "TRANSPONDER CODE:1": 1200,
                        "TRANSPONDER STATE:1": 1,
                    },
                    # Camouflage as MSFS Sidecar
                    "name": "MSFS", 
                    "version": "1.0.0",
                    "adapter_version": "1.0.0",
                    "simapi_version": "1.0",
                    "exe": "msfs.exe" 
                }
            }
            try:
                r = requests.post(url, json=data, timeout=1)
                # print(f"Telemetry Status: {r.status_code}") # Silent unless error
            except:
                pass
            time.sleep(0.5)

    def stop(self):
        self.stop_event.set()

def verify_session_persistence(api_key):
    # 0. Start Telemetry FIRST (to seed session)
    logger.info("0. Starting Telemetry (MSFS Camouflage)...")
    t_sender = TelemetrySender(api_key, 33.5799, -117.1223, 1350, 100)
    t_sender.start()
    
    time.sleep(2)

    # 1. Start Flight (Minimal)
    logger.info("1. Calling startFlight (Minimal GET)...")
    try:
        r = requests.get("https://apipri.stratus.ai/sapi/startFlight", params={"api_key": api_key})
        logger.info(f"   startFlight: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"   startFlight Error: {e}")

    # 2. Assign Gate
    logger.info("2. Assigning Gate (F70 / RAMP 1)...")
    try:
        r = requests.get("https://apipri.stratus.ai/sapi/assignGate", 
                         params={"api_key": api_key, "icao": "F70", "gate": "RAMP 1"})
        logger.info(f"   assignGate: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"   assignGate Error: {e}")

    # 3. Radio Check
    logger.info("3. Triggering Radio Check...")
    try:
        r = requests.get("https://apipri.stratus.ai/sapi/sayAs", 
            params={
                "api_key": api_key,
                "message": "Radio Check",
                "channel": "COM1",
                "entity": "atc" 
            })
        logger.info(f"   sayAs: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"   sayAs Error: {e}")

    # 4. Check History
    logger.info("4. Checking History...")
    start_time = time.time()
    while time.time() - start_time < 5:
        try:
            r = requests.get("https://apipri.stratus.ai/sapi/getCommsHistory", params={"api_key": api_key})
            if r.status_code == 200:
                data = r.json()
                hist = data.get("comm_history", [])
                if hist:
                    first = hist[0]
                    if "checking" in first.get('incoming_message', '') or "French Valley" in first.get('station_name', ''):
                        logger.info("   SUCCESS: F70 session confirmed!")
                        break
        except:
            pass
        time.sleep(1)
        
    t_sender.stop()
    t_sender.join()

if __name__ == "__main__":
    verify_session_persistence(load_api_key())
