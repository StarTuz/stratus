
import requests
import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

USERNAME = os.environ.get("SI_USERNAME")
PASSWORD = os.environ.get("SI_PASSWORD")
AUTH_URL = "https://lambda.stratus.ai/auth/login"

def test_login():
    if not USERNAME or not PASSWORD:
        logger.error("Error: SI_USERNAME and SI_PASSWORD must be set.")
        return

    logger.info(f"Attempting login to {AUTH_URL} as {USERNAME}...")
    
    try:
        payload = {"username": USERNAME, "password": PASSWORD}
        headers = {"Content-Type": "application/json"}
        
        r = requests.post(AUTH_URL, json=payload, headers=headers, timeout=10)
        
        logger.info(f"Status Code: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            logger.info("Login Successful!")
            logger.info(f"Keys returned: {list(data.keys())}")
            
            # Print potentially interesting fields (masking full token)
            if 'token' in data:
                logger.info(f"Token (first 20 chars): {data['token'][:20]}...")
            if 'refreshToken' in data:
                logger.info(f"RefreshToken (first 20 chars): {data['refreshToken'][:20]}...")
            if 'user' in data:
                logger.info(f"User Data: {json.dumps(data.get('user'), indent=2)}")
            if 'api_key' in data:
                logger.info(f"API API KEY FOUND: {data['api_key']}")
                
            # Dump full response to debug_auth_response.json for inspection (careful with secrets)
            with open("debug_auth_response.json", "w") as f:
                json.dump(data, f, indent=2)
                
        else:
            logger.error(f"Login Failed: {r.text}")

    except Exception as e:
        logger.error(f"Error during login: {e}")

if __name__ == "__main__":
    test_login()
