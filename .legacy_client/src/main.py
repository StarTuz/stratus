#!/usr/bin/env python3
"""
StratusATC - Native Mac/Linux Client

Main entry point for the application.

Usage:
    python main.py           # Launch GUI + ComLink web server
    python main.py --cli     # Launch CLI mode
    python main.py --web     # Launch web server only (headless mode)
    python main.py --no-web  # Launch GUI without web server
    python main.py --help    # Show help
"""

import sys
import os
import argparse
import logging

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        description='StratusATC - Native Mac/Linux Client',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
    Default (no args)    Launch GUI with ComLink web server
    --cli                Launch interactive command-line interface
    --web                Launch only the web server (headless/audio-only mode)
    --no-web             Launch GUI without the web server
    
ComLink:
    When the web server is enabled (default), access the touch-friendly
    interface from any device on your network at:
    
        http://localhost:8080/comlink
    
    This is ideal for:
    - Fullscreen flight sim users who can't alt-tab
    - VR users who need a companion device
    - Multi-monitor setups
    - Tablet/phone control
    
For CLI-only usage, see: python cli.py --help
"""
    )
    
    parser.add_argument('--cli', action='store_true',
                        help='Launch in CLI mode instead of GUI')
    parser.add_argument('--web', action='store_true',
                        help='Launch only the ComLink web server (headless mode)')
    parser.add_argument('--no-web', action='store_true',
                        help='Launch GUI without the ComLink web server')
    parser.add_argument('--port', type=int, default=8080,
                        help='Port for the ComLink web server (default: 8080)')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.cli:
        # Launch CLI
        from cli import StratusCLI
        cli = StratusCLI()
        cli.cmdloop()
    elif args.web:
        # Headless mode - web server only with audio playback
        print("=" * 60)
        print("  StratusATC - Headless Mode (Web + Audio Only)")
        print("=" * 60)
        run_headless(port=args.port)
    else:
        # Check for plugin installation before starting GUI
        try:
            from core.sim_installer import check_and_install
            check_and_install()
        except Exception as e:
            logging.error(f"Failed to run auto-installer: {e}")
            
        # Launch GUI (with web server unless --no-web)
        from ui import run_gui
        run_gui(enable_web=not args.no_web, web_port=args.port)


def run_headless(port: int = 8080):
    """
    Run in headless mode - no GUI, just web server and audio.
    
    This mode is perfect for:
    - Running on a server/dedicated machine
    - Users who only want web interface + audio
    - Low-resource environments
    """
    import time
    import signal
    
    from web import ComLinkServer
    from core.providers.factory import get_provider, IATCProvider
    from core.sim_data import SimDataInterface
    from audio import AudioHandler
    
    # Initialize services
    # Config path handling is internal to factory now
    sapi: IATCProvider = get_provider()
    audio = AudioHandler()
    sim_data = SimDataInterface()
    
    # Initialize ComLink server
    comlink = ComLinkServer(port=port)
    
    # Track played communications
    played_comm_ids = set()
    
    # Wire up ComLink callbacks
    def on_send_transmission(message: str, channel: str):
        if sapi.get_status().startswith("CONNECTED"):
            from core.providers.base import Channel
            # Map string channel to Enum if needed, or pass string directly if provider handles it
            # Local provider handles strings "left"/"right"/"com1" etc.
            response = sapi.say(message, channel=channel)
            if response.success:
                comlink.send_toast("Transmission sent", "success")
            else:
                comlink.send_toast(f"Failed: {response.error}", "error")
    
    def on_swap_frequency(channel: str):
        if channel == "COM1":
            sim_data.swap_com1()
        else:
            sim_data.swap_com2()
    
    def on_play_audio(url: str):
        audio.queue_atc_audio(url, "ATC", "", "")
    
    comlink.on_send_transmission = on_send_transmission
    comlink.on_swap_frequency = on_swap_frequency
    comlink.on_play_audio = on_play_audio
    
    # Start ComLink
    comlink.start()
    
    print(f"\n📻 ComLink available at: http://localhost:{port}/comlink")
    print(f"   Access from any device on your network!")
    print(f"\nPress Ctrl+C to stop\n")
    
    # Connect to SAPI / Local Provider
    print("Connecting to ATC Provider...")
    if sapi.connect():
        print(f"✓ Connected: {sapi.get_status()}")
        comlink.update_connection_status(True, sapi.get_status())
    else:
        print("✗ Failed to connect to Provider")
        comlink.update_connection_status(False, "Not connected")
    
    # Main loop
    running = True
    
    def handle_signal(signum, frame):
        nonlocal running
        running = False
        print("\nShutting down...")
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    poll_interval = 5  # seconds
    last_poll = 0
    
    while running:
        try:
            now = time.time()
            
            # Update telemetry
            telemetry = sim_data.read_telemetry()
            comlink.update_telemetry({
                "com1": {
                    "active": telemetry.com1.active,
                    "standby": telemetry.com1.standby,
                    "power": telemetry.com1.power
                },
                "com2": {
                    "active": telemetry.com2.active,
                    "standby": telemetry.com2.standby,
                    "power": telemetry.com2.power
                },
                "transponder": {
                    "code": telemetry.transponder.code,
                    "mode": telemetry.transponder.mode
                }
            })
            
            # Poll for new comms (Cloud only)
            # Local provider handles audio output directly via SpeechD-NG
            if "CLOUD" in sapi.get_status() and now - last_poll >= poll_interval:
                last_poll = now
                # Note: We need to expose get_comms_history in base if we want this common
                # For now, we assume Cloud provider might have it or we cast it
                if hasattr(sapi, 'get_comms_history'):
                    response = sapi.get_comms_history()
                if response.success and response.data:
                    # Convert to dicts for JSON
                    comms = []
                    for entry in response.data:
                        comms.append({
                            "station_name": entry.station_name,
                            "frequency": entry.frequency,
                            "incoming_message": entry.incoming_message,
                            "outgoing_message": entry.outgoing_message,
                            "atc_url": entry.atc_url
                        })
                        
                        # Auto-play new audio
                        if entry.atc_url:
                            comm_id = hash(entry.atc_url)
                            if comm_id not in played_comm_ids:
                                played_comm_ids.add(comm_id)
                                audio.queue_atc_audio(
                                    entry.atc_url,
                                    entry.station_name,
                                    entry.frequency,
                                    entry.outgoing_message
                                )
                    
                    comlink.update_comms(comms)
            
            time.sleep(0.5)
            
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(1)
    
    # Cleanup
    audio.shutdown()
    comlink.stop()
    print("Goodbye!")


if __name__ == "__main__":
    main()

