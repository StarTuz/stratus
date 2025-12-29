
import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

API_KEY = "s4GH8119xFyX"
DATA_DIR = os.path.expanduser("~/.local/share/SayIntentionsAI")
FLIGHT_FILE = os.path.join(DATA_DIR, "flight.json")

def create_flight_json():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        
    payload = {
      "flight_details": {
        "Email": "linux_user@example.com", 
        "userid": "linux_user_01",
        "flight_id": 123456, 
        "api_key": API_KEY,
        "hostname": "https://apipri.sayintentions.ai",
        "callsign": "N123AB",
        "callsign_icao": "N123AB",
        "current_flight": {
          "flight_origin": "F70", 
          "flight_destination": "KLAX",
          "assigned_gate": "RAMP 1",
          "taxi_path": [],
          "flight_plan_route": "F70..KLAX"
        },
        "traffic_enabled": "1",
        "traffic_density": "medium",
        "atis_airports": "F70,KLAX",
        "current_airport": "F70"
      }
    }
    
    try:
        with open(FLIGHT_FILE, 'w') as f:
            json.dump(payload, f, indent=2)
        logger.info(f"Successfully created {FLIGHT_FILE}")
        logger.info(json.dumps(payload, indent=2))
    except Exception as e:
        logger.error(f"Failed to create flight.json: {e}")

if __name__ == "__main__":
    create_flight_json()
