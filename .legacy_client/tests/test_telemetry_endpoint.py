
import requests
import configparser
import os
import json

def test_telemetry():
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_key = config.get('sapi', 'api_key', fallback=None)
    
    if not api_key:
        print("API Key not found in config.ini")
        return

    # Testing correct SAPI v1 input endpoint
    url = f"https://apipri.stratus.ai/sapi/v1/input?api_key={api_key}"
    
    # Exhaustive F70 French Valley telemetry
    data = {
        "sim": {
            "variables": {
                "PLANE LATITUDE": 33.58,
                "PLANE LONGITUDE": -117.12,
                "PLANE ALTITUDE": 1345.0,
                "INDICATED ALTITUDE": 1345.0,
                "PLANE ALT ABOVE GROUND MINUS CG": 0,
                "SIM ON GROUND": 1,
                "MAGNETIC COMPASS": 95,
                "PLANE HEADING DEGREES TRUE": 106,
                "AIRSPEED INDICATED": 0,
                "AIRSPEED TRUE": 0,
                "VERTICAL SPEED": 0,
                "COM ACTIVE FREQUENCY:1": 133.5,
                "COM STANDBY FREQUENCY:1": 119.025,
                "COM RECEIVE:1": 1,
                "COM TRANSMIT:1": 1,
                "COM ACTIVE FREQUENCY:2": 119.725,
                "COM RECEIVE:2": 0,
                "TRANSPONDER CODE:1": 1200,
                "TRANSPONDER STATE:1": 4,
                "ENGINE TYPE": 0,
                "TOTAL WEIGHT": 2500,
                "TITLE": "C-FIJM",
                "ATC MODEL": "M7"
            },
            "exe": "StratusATC_Test.exe",
            "simapi_version": "1.0",
            "name": "X-Plane 12 (Test)",
            "version": "1.0.0",
            "adapter_version": "1.0.0"
        }
    }
    # Try forcing location via setVar
    print("\nForcing location via setVar...")
    requests.get("https://apipri.stratus.ai/sapi/setVar", params={"api_key": api_key, "name": "PLANE LATITUDE", "value": "33.58"})
    requests.get("https://apipri.stratus.ai/sapi/setVar", params={"api_key": api_key, "name": "PLANE LONGITUDE", "value": "-117.12"})
    
    import time

    for i in range(2):
        print(f"[{i+1}/2] Testing POST to {url}...")
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code} Body: {response.text}")
        time.sleep(1)


    # Also test getCommsHistory to see if it lists F70 stations now
    params = {"api_key": api_key}
    print("\nWaiting 2 seconds for server to process...")

    time.sleep(2)
    print("Testing getCommsHistory...")
    # Formal Frequency Update
    print("\nSetting frequency to 133.500 via setFreq...")
    freq_params = {
        "api_key": api_key,
        "freq": "133.500",
        "channel": "COM1"
    }
    resp_freq = requests.get("https://apipri.stratus.ai/sapi/setFreq", params=freq_params)
    print(f"Status Code: {resp_freq.status_code} Body: {resp_freq.text}")

    # Try a Radio Check at F70 frequency (133.500)
    print("\nTesting sayAs 'Radio Check' on 133.500...")

    say_params = {
        "api_key": api_key,
        "message": "Radio Check",
        "channel": "COM1",
        "entity": "atc"
    }
    resp_say = requests.get("https://apipri.stratus.ai/sapi/sayAs", params=say_params)
    print(f"Status Code: {resp_say.status_code} Body: {resp_say.text}")
    
    print("\nWaiting 5 seconds for ATC response...")
    time.sleep(5)
    
    print("Testing getCommsHistory again...")
    resp_history = requests.get("https://apipri.stratus.ai/sapi/getCommsHistory", params=params)
    if resp_history.status_code == 200:
        history = resp_history.json().get("comm_history", [])
        print(f"Found {len(history)} comm entries")
        for entry in history:
            print(f" - {entry.get('station_name')} ({entry.get('frequency')}): {entry.get('incoming_message')[:50]}")
            print(f"   ATC Response: {entry.get('outgoing_message')[:50]}")



if __name__ == "__main__":
    test_telemetry()
