#!/usr/bin/env python3
"""
Audio Module Test Script

Tests the audio download and playback functionality.
Can be run standalone or used as a quick sanity check.

Usage:
    # Test with a sample audio URL (requires API key for real URLs)
    python test_audio.py

    # Test with a specific MP3 file
    python test_audio.py /path/to/audio.mp3

    # Test with a real Stratus audio URL
    python test_audio.py "https://siaudio.s3.us-west-1.amazonaws.com/XXXX.mp3"
"""

import sys
import os
import time
import logging
import argparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from audio import AudioHandler, AudioDownloader, AudioPlayer, PlayerState

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_downloader():
    """Test the audio downloader component."""
    print("\n" + "="*60)
    print("Testing AudioDownloader")
    print("="*60)
    
    downloader = AudioDownloader()
    
    # Show cache stats
    file_count, total_bytes = downloader.get_cache_stats()
    print(f"Cache stats: {file_count} files, {total_bytes} bytes")
    print(f"Cache directory: {downloader.cache_dir}")
    
    # Test URL to cache key conversion
    test_url = "https://siaudio.s3.us-west-1.amazonaws.com/R26isgM5tKoFg82rSbTa.mp3"
    cache_key = downloader._url_to_cache_key(test_url)
    print(f"URL cache key: {cache_key}")
    
    return True


def test_player():
    """Test the audio player component."""
    print("\n" + "="*60)
    print("Testing AudioPlayer")
    print("="*60)
    
    player = AudioPlayer()
    
    # List available devices
    devices = player.list_devices()
    print(f"Found {len(devices)} audio output devices:")
    for dev in devices[:5]:  # Show first 5
        default = " (default)" if dev['is_default'] else ""
        print(f"  [{dev['index']}] {dev['name']}{default}")
    
    # Test volume controls
    original_volume = player.get_volume()
    player.set_volume(0.5)
    assert player.get_volume() == 0.5
    player.set_volume(original_volume)
    print(f"Volume control: OK")
    
    # Test state
    assert player.state == PlayerState.IDLE
    print(f"Initial state: {player.state.value}")
    
    player.stop()
    return True


def test_handler():
    """Test the high-level audio handler."""
    print("\n" + "="*60)
    print("Testing AudioHandler")
    print("="*60)
    
    handler = AudioHandler()
    
    # Set up callbacks
    events = []
    
    def on_playback_start(item):
        events.append(('start', item.station_name))
        print(f"  → Playback started: {item.station_name}")
    
    def on_playback_complete(item):
        events.append(('complete', item.station_name))
        print(f"  → Playback complete: {item.station_name}")
    
    def on_state_change(state):
        events.append(('state', state.value))
        print(f"  → State changed: {state.value}")
    
    handler.on_playback_start = on_playback_start
    handler.on_playback_complete = on_playback_complete
    handler.on_state_change = on_state_change
    
    print(f"Handler initialized, state: {handler.state.value}")
    print(f"Cache stats: {handler.get_cache_stats()}")
    
    handler.shutdown()
    return True


def test_with_url(url: str):
    """Test downloading and playing audio from a URL."""
    print("\n" + "="*60)
    print(f"Testing with URL: {url[:50]}...")
    print("="*60)
    
    handler = AudioHandler()
    
    # Track completion
    playback_done = False
    
    def on_complete(item):
        nonlocal playback_done
        playback_done = True
        print(f"\n✓ Playback complete: {item.message or 'No message'}")
    
    def on_start(item):
        print(f"\n▶ Playing: {item.station_name or 'Unknown station'}")
    
    handler.on_playback_start = on_start
    handler.on_playback_complete = on_complete
    
    # Queue the audio
    success = handler.queue_atc_audio(
        url=url,
        station_name="Test Station",
        frequency="123.45",
        message="This is a test audio message"
    )
    
    if not success:
        print("✗ Failed to queue audio")
        return False
    
    print(f"Audio queued, waiting for playback...")
    
    # Wait for playback to complete (max 60 seconds)
    timeout = 60
    start_time = time.time()
    
    while not playback_done and (time.time() - start_time) < timeout:
        time.sleep(0.1)
        # Show a simple progress indicator
        if int(time.time() - start_time) % 5 == 0:
            print(f"  ... playing ({handler.state.value})")
    
    if not playback_done:
        print(f"✗ Playback timed out after {timeout}s")
        handler.shutdown()
        return False
    
    handler.shutdown()
    return True


def test_with_file(file_path: str):
    """Test playing a local audio file."""
    print("\n" + "="*60)
    print(f"Testing with file: {file_path}")
    print("="*60)
    
    from pathlib import Path
    
    path = Path(file_path)
    if not path.exists():
        print(f"✗ File not found: {file_path}")
        return False
    
    player = AudioPlayer()
    
    playback_done = False
    
    def on_complete():
        nonlocal playback_done
        playback_done = True
    
    player.queue_file(path, on_complete=on_complete)
    
    print(f"Playing {path.name}...")
    
    # Wait for playback
    timeout = 120
    start_time = time.time()
    
    while not playback_done and (time.time() - start_time) < timeout:
        time.sleep(0.1)
    
    if playback_done:
        print("✓ Playback complete")
    else:
        print(f"✗ Playback timed out")
    
    player.stop()
    return playback_done


def main():
    parser = argparse.ArgumentParser(description='Test audio module')
    parser.add_argument('source', nargs='?', help='URL or file path to test with')
    parser.add_argument('--skip-unit', action='store_true', help='Skip unit tests')
    args = parser.parse_args()
    
    print("="*60)
    print("StratusATC Audio Module Test")
    print("="*60)
    
    results = []
    
    # Run unit tests
    if not args.skip_unit:
        results.append(("Downloader", test_downloader()))
        results.append(("Player", test_player()))
        results.append(("Handler", test_handler()))
    
    # Test with source if provided
    if args.source:
        if args.source.startswith('http'):
            results.append(("URL Playback", test_with_url(args.source)))
        else:
            results.append(("File Playback", test_with_file(args.source)))
    
    # Summary
    print("\n" + "="*60)
    print("Test Results")
    print("="*60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("All tests passed! ✓")
    else:
        print("Some tests failed. ✗")
        sys.exit(1)


if __name__ == "__main__":
    main()
