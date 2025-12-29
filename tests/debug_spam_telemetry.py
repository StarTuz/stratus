
import requests
import configparser
import time
import json
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def load_api_key():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config.get('sapi', 'api_key')

API_KEY = load_api_key()
TELEM_URL = "https://apipri.stratus.ai/sapi/v1/input"
HIST_URL = "https://apipri.stratus.ai/sapi/getCommsHistory"

def spam_moving_telemetry():
    logger.info(f"Starting AIRBORNE telemetry flood to {TELEM_URL}...")
    headers = {
        "X-API-Key": API_KEY, 
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) StratusClient/1.0"
    }
    
    lat = 33.5800
    lon = -117.1200
    alt = 3000
    
    for i in range(30):
        try:
            # Simulate movement (flying east)
            lon += 0.001
            alt += 10
            
            payload = {
                "sim": {
                    "variables": {
                        "PLANE LATITUDE": f"{lat:.6f}",
                        "PLANE LONGITUDE": f"{lon:.6f}",
                        "PLANE ALTITUDE": int(alt),
                        "INDICATED ALTITUDE": int(alt),
                        "SIM ON GROUND": 0, # Airborne!
                        "PLANE HEADING DEGREES TRUE": 90,
                        "MAGNETIC COMPASS": 90,
                        "PLANE PITCH DEGREES": 5,    
                        "PLANE BANK DEGREES": 0,
                        "AIRSPEED INDICATED": 100, # Flying!
                        "AIRSPEED TRUE": 110,
                        "VERTICAL SPEED": 500, # Climbing
                        "COM ACTIVE FREQUENCY:1": "122.800",
                        "COM STANDBY FREQUENCY:1": "118.000",
                        "COM TRANSMIT:1": 1,
                        "COM RECEIVE:1": 1,
                        "TRANSPONDER CODE:1": 1200,
                        "TRANSPONDER STATE:1": 1,
                        "Title": "C172",
                        "ATC MODEL": "C172",
                        "LOCAL TIME": time.time() % 86400,
                        "ZULU TIME": time.time() % 86400
                    },
                    "name": "X-Plane 12 (Native)",
                    "exe": "X-Plane.exe", 
                    "simapi_version": "1.0",
                    "version": "1.0.0",
                    "adapter_version": "1.0.0"
                }
            }
            
            # Use X-API-Key header AND param just in case
            r = requests.post(f"{TELEM_URL}?api_key={API_KEY}", json=payload, headers=headers, timeout=2)
            if r.status_code != 200:
                logger.error(f"Telem Fail: {r.status_code} {r.text}")
        except Exception as e:
            logger.error(f"Telem Err: {e}")
        time.sleep(1)

def poll_history():
    logger.info("Starting history polling...")
    for i in range(10):
        try:
            r = requests.get(HIST_URL, params={"api_key": API_KEY}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                hist = data.get("comm_history", [])
                if hist:
                    last = hist[0]
                    # Log the full first item to check for updates
                    logger.info(f"Last Msg: {last.get('stamp_zulu')} - {last.get('station_name')}")
            else:
                 logger.error(f"Hist Fail: {r.status_code}")
        except Exception as e:
             logger.error(f"Hist Err: {e}")
        time.sleep(3)

if __name__ == "__main__":
    t1 = threading.Thread(target=spam_moving_telemetry)
    t2 = threading.Thread(target=poll_history)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
