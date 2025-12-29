
import requests
import json
import logging
import os
import websocket
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

USERNAME = os.environ.get("SI_USERNAME")
PASSWORD = os.environ.get("SI_PASSWORD")
AUTH_URL = "https://lambda.stratus.ai/auth/login"

def get_token():
    r = requests.post(AUTH_URL, json={"username": USERNAME, "password": PASSWORD}, timeout=10)
    return r.json().get("token")

def test_comlink():
    token = get_token()
    if not token:
        logger.error("No token")
        return
    
    # Try WebSocket connection to comlink
    ws_urls = [
        "wss://lambda.stratus.ai/comlink",
        "wss://comlink.stratus.ai",
        "wss://comlink.stratus.ai/",
        "wss://comlink.stratus.ai/socket",
        "wss://comlink.stratus.ai/ws",
    ]
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Origin": "https://portal.stratus.ai"
    }
    
    for url in ws_urls:
        logger.info(f"Trying WebSocket: {url}...")
        try:
            ws = websocket.create_connection(url, timeout=3, header=[f"Authorization: Bearer {token}"])
            logger.info(f"   CONNECTED! Receiving...")
            ws.send(json.dumps({"type": "ping"}))
            result = ws.recv()
            logger.info(f"   Received: {result[:200]}")
            ws.close()
        except Exception as e:
            # Check if it's a "101 switching protocols" error (which means WS is supported)
            if "101" in str(e):
                logger.info(f"   WebSocket handshake started...")
            else:
                logger.info(f"   {e}")

    # Also try HTTP long-polling version
    logger.info("\nTrying HTTP comlink...")
    headers_http = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get("https://lambda.stratus.ai/comlink?type=sim", headers=headers_http, timeout=5)
        logger.info(f"HTTP comlink: {r.status_code} {r.text[:100]}")
    except Exception as e:
        logger.error(e)

if __name__ == "__main__":
    test_comlink()
