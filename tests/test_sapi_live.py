#!/usr/bin/env python3
"""
Live SAPI API Test Script

Tests the SAPI module against the real SayIntentions API.
Requires a valid API key in config.ini and preferably X-Plane running.
"""

import sys
import os
import logging

# Add client/src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "client", "src"))

from core.sapi_interface import (
    SapiService,
    Channel,
    Entity,
    create_sapi_service
)


def setup_logging():
    """Configure logging for test output"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S"
    )


def print_header(title: str):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)


def test_connection(sapi: SapiService) -> bool:
    """Test API connection"""
    print_header("Testing API Connection")
    
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.ini")
    success = sapi.connect()
    
    print(f"Status: {sapi.get_status()}")
    print(f"Connected: {sapi.is_connected}")
    
    return success


def test_comms_history(sapi: SapiService):
    """Test getCommsHistory endpoint"""
    print_header("Testing getCommsHistory")
    
    response = sapi.get_comms_history()
    
    if not response.success:
        print(f"❌ Failed: {response.error}")
        return
    
    entries = response.data
    print(f"✓ Retrieved {len(entries)} communication entries")
    
    for i, entry in enumerate(entries[:5], 1):  # Show max 5 entries
        print(f"\n--- Entry {i} ---")
        print(f"  Station: {entry.station_name} ({entry.ident})")
        print(f"  Frequency: {entry.frequency}")
        print(f"  Pilot: {entry.incoming_message[:80]}..." if len(entry.incoming_message) > 80 else f"  Pilot: {entry.incoming_message}")
        print(f"  ATC: {entry.outgoing_message[:80]}..." if len(entry.outgoing_message) > 80 else f"  ATC: {entry.outgoing_message}")
        if entry.atc_url:
            print(f"  🔊 Audio URL: {entry.atc_url[:60]}...")


def test_weather(sapi: SapiService, icao: str = "KTRK"):
    """Test getWX endpoint"""
    print_header(f"Testing getWX for {icao}")
    
    response = sapi.get_weather(icao)
    
    if not response.success:
        print(f"❌ Failed: {response.error}")
        return
    
    wx = response.data
    print(f"✓ Weather for {wx.icao}:")
    print(f"  METAR: {wx.metar or '(none)'}")
    print(f"  TAF: {wx.taf[:100] if wx.taf else '(none)'}...")
    print(f"  ATIS: {wx.atis[:100] if wx.atis else '(none)'}...")


def test_parking(sapi: SapiService):
    """Test getParking endpoint"""
    print_header("Testing getParking")
    
    response = sapi.get_parking()
    
    if not response.success:
        print(f"❌ Failed: {response.error}")
        return
    
    parking = response.data
    print(f"✓ Parking Info:")
    print(f"  Gate: {parking.gate}")
    print(f"  Position: {parking.latitude:.6f}, {parking.longitude:.6f}")
    print(f"  Heading: {parking.heading}°")


def test_audio_download(sapi: SapiService):
    """Test audio download from comm history"""
    print_header("Testing Audio Download")
    
    response = sapi.get_comms_history()
    
    if not response.success or not response.data:
        print("❌ No comms history available for audio test")
        return
    
    # Find first entry with audio URL
    for entry in response.data:
        if entry.atc_url:
            print(f"Downloading audio from: {entry.atc_url[:60]}...")
            
            audio_data = sapi.download_audio(entry.atc_url)
            
            if audio_data:
                print(f"✓ Downloaded {len(audio_data)} bytes")
                
                # Save to temp for verification
                temp_path = "/tmp/sapi_test_audio.mp3"
                sapi.download_audio(entry.atc_url, temp_path)
                print(f"✓ Saved to {temp_path}")
            else:
                print("❌ Failed to download audio")
            
            return
    
    print("⚠ No audio URLs in comm history")


def test_say_as(sapi: SapiService, message: str = None):
    """Test sayAs endpoint (sending pilot message)"""
    print_header("Testing sayAs")
    
    if not message:
        message = "Request flight following to Sacramento"
    
    print(f"Sending message: '{message}'")
    
    response = sapi.say_as(
        message=message,
        channel=Channel.COM1,
        entity=Entity.ATC
    )
    
    if response.success:
        print(f"✓ Message sent successfully")
        print(f"  Response: {response.data}")
    else:
        print(f"❌ Failed: {response.error}")


def main():
    setup_logging()
    
    print("\n" + "="*60)
    print(" SAPI Live API Test Suite")
    print(" SayIntentions.AI Native Client")
    print("="*60)
    
    # Find config
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.ini")
    
    if not os.path.exists(config_path):
        print(f"\n❌ Config not found at: {config_path}")
        print("Please create config.ini with your API key")
        return 1
    
    # Create service
    sapi = SapiService(config_path=config_path)
    
    # Run tests
    if not test_connection(sapi):
        print("\n❌ Connection failed. Check API key and network.")
        return 1
    
    test_comms_history(sapi)
    test_weather(sapi, "KTRK")  # Truckee - from the previous session
    test_parking(sapi)
    test_audio_download(sapi)
    
    # Uncomment to test sending (requires active session):
    # test_say_as(sapi, "Truckee traffic, Cessna 123AB departing runway 20")
    
    print_header("Test Complete")
    print("All read-only tests passed! ✓")
    print("\nNote: sayAs test is commented out to avoid sending test messages.")
    print("Uncomment in code to test pilot transmissions.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
