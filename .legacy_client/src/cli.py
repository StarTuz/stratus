#!/usr/bin/env python3
"""
Stratus CLI Client

A command-line interface for testing and using the Stratus API.
This serves as both a development tool and a minimal working client.

Usage:
    python cli.py                    # Start interactive mode
    python cli.py --status           # Check connection status
    python cli.py --history          # Fetch and display comms history
    python cli.py --play             # Fetch history and play audio
    python cli.py --say "message"    # Send a pilot transmission
"""

import sys
import os
import cmd
import time
import argparse
import logging
import threading
from typing import Optional, List, Set
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.sapi_interface import (
    SapiService, CommEntry, Channel, Entity, 
    create_sapi_service, SapiResponse
)
from audio import AudioHandler, PlayerState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cli")


class StratusCLI(cmd.Cmd):
    """Interactive CLI for StratusATC"""
    
    intro = """
╔══════════════════════════════════════════════════════════════════╗
║           StratusATC - Native Mac/Linux Client              ║
║                    CLI Test Harness v0.1                         ║
╚══════════════════════════════════════════════════════════════════╝

Type 'help' for available commands.
Type 'connect' to connect to the SAPI server.
Type 'quit' or 'exit' to exit.
"""
    prompt = 'SAPI> '
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
        self.config_path = config_path
        self.sapi: Optional[SapiService] = None
        self.audio: Optional[AudioHandler] = None
        
        # Track which comm entries we've already played to avoid duplicates
        self._played_comm_ids: Set[int] = set()
        
        # Polling state
        self._polling = False
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_interval = 2.0  # seconds
    
    def preloop(self):
        """Initialize before command loop starts."""
        # Try to find config and auto-connect
        config_locations = [
            self.config_path,
            os.path.expanduser("~/.config/stratusatc/config.ini"),
            os.path.join(os.path.dirname(__file__), "..", "..", "config.ini"),
        ]
        
        for path in config_locations:
            if path and os.path.exists(path):
                self.config_path = path
                print(f"Found config: {path}")
                break
        
        # Initialize audio handler
        self.audio = AudioHandler()
        self._setup_audio_callbacks()
    
    def _setup_audio_callbacks(self):
        """Set up callbacks for audio playback events."""
        def on_start(item):
            station = item.station_name or "Unknown"
            freq = item.frequency or "---"
            print(f"\n🔊 [{freq}] {station}")
            if item.message:
                # Show first 80 chars of message
                msg = item.message[:80] + "..." if len(item.message) > 80 else item.message
                print(f"   \"{msg}\"")
        
        def on_complete(item):
            print(f"   ✓ Audio complete")
            # Re-show prompt
            print(self.prompt, end='', flush=True)
        
        self.audio.on_playback_start = on_start
        self.audio.on_playback_complete = on_complete
    
    def postcmd(self, stop, line):
        """Hook after each command."""
        # Add a blank line for readability
        if line.strip() not in ['quit', 'exit', 'EOF']:
            print()
        return stop
    
    # =========================================================================
    # Connection Commands
    # =========================================================================
    
    def do_connect(self, arg):
        """Connect to the Stratus API server.
        
        Usage: connect [api_key]
        
        If no API key is provided, will try to load from config.ini
        """
        print("Connecting to Stratus API...")
        
        api_key = arg.strip() if arg else None
        
        try:
            self.sapi = SapiService(api_key=api_key, config_path=self.config_path)
            
            if self.sapi.connect():
                self.prompt = 'SAPI[✓]> '
                print("✓ Connected successfully!")
            else:
                self.prompt = 'SAPI[✗]> '
                print("✗ Connection failed. Check your API key.")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    def do_status(self, arg):
        """Show current connection status."""
        if not self.sapi:
            print("Status: NOT INITIALIZED")
            print("  Use 'connect' to initialize the SAPI client.")
            return
        
        status = self.sapi.get_status()
        print(f"Status: {status}")
        
        if self.audio:
            print(f"Audio: {self.audio.state.value}")
            print(f"Audio Queue: {self.audio.queue_size} items")
            cache_files, cache_bytes = self.audio.get_cache_stats()
            print(f"Audio Cache: {cache_files} files ({cache_bytes // 1024} KB)")
        
        if self._polling:
            print(f"Polling: ACTIVE (every {self._poll_interval}s)")
    
    def do_disconnect(self, arg):
        """Disconnect from the API."""
        if self._polling:
            self.do_stop_poll(None)
        
        self.sapi = None
        self.prompt = 'SAPI> '
        print("Disconnected.")
    
    # =========================================================================
    # Communication Commands
    # =========================================================================
    
    def do_history(self, arg):
        """Fetch and display communication history.
        
        Usage: history [count]
        
        Shows recent ATC/pilot communications.
        """
        if not self._check_connected():
            return
        
        count = int(arg) if arg else 10
        
        response = self.sapi.get_comms_history()
        
        if not response.success:
            print(f"✗ Failed to fetch history: {response.error}")
            return
        
        entries: List[CommEntry] = response.data or []
        
        if not entries:
            print("No communication history found.")
            return
        
        print(f"\n{'='*60}")
        print(f"Communication History ({len(entries)} entries)")
        print(f"{'='*60}")
        
        for i, entry in enumerate(entries[:count]):
            has_audio = "🔊" if entry.atc_url else "  "
            print(f"\n{has_audio} [{entry.frequency}] {entry.station_name} ({entry.ident})")
            if entry.incoming_message:
                print(f"   PILOT: {entry.incoming_message}")
            if entry.outgoing_message:
                print(f"   ATC:   {entry.outgoing_message}")
    
    def do_play(self, arg):
        """Fetch history and play any audio.
        
        Usage: play [index]
        
        If index is provided, plays that specific entry.
        Otherwise plays all new audio entries.
        """
        if not self._check_connected():
            return
        
        response = self.sapi.get_comms_history()
        
        if not response.success:
            print(f"✗ Failed to fetch history: {response.error}")
            return
        
        entries: List[CommEntry] = response.data or []
        
        if arg:
            # Play specific entry
            try:
                idx = int(arg)
                if 0 <= idx < len(entries):
                    entry = entries[idx]
                    self._play_entry(entry, force=True)
                else:
                    print(f"Invalid index. Valid range: 0-{len(entries)-1}")
            except ValueError:
                print("Usage: play [index]")
        else:
            # Play all entries with audio
            queued = 0
            for entry in entries:
                if entry.atc_url:
                    if self._play_entry(entry):
                        queued += 1
            
            if queued > 0:
                print(f"Queued {queued} audio files for playback.")
            else:
                print("No new audio to play.")
    
    def _play_entry(self, entry: CommEntry, force: bool = False) -> bool:
        """Play audio for a comm entry."""
        if not entry.atc_url:
            return False
        
        # Use URL as ID for deduplication
        comm_id = hash(entry.atc_url)
        
        if not force and comm_id in self._played_comm_ids:
            return False
        
        self._played_comm_ids.add(comm_id)
        
        return self.audio.queue_atc_audio(
            url=entry.atc_url,
            station_name=entry.station_name,
            frequency=entry.frequency,
            message=entry.outgoing_message
        )
    
    def do_say(self, arg):
        """Send a pilot transmission.
        
        Usage: say <message>
        
        Examples:
            say Request flight following to Sacramento Executive
            say Cancel flight following
            say Request taxi to runway 27
        """
        if not self._check_connected():
            return
        
        if not arg:
            print("Usage: say <message>")
            return
        
        print(f"Transmitting: \"{arg}\"")
        response = self.sapi.say_as(arg, Channel.COM1, Entity.ATC)
        
        if response.success:
            print("✓ Transmission sent")
            # Wait a moment then check for response
            print("  Waiting for ATC response...")
            time.sleep(2)
            self.do_play("")
        else:
            print(f"✗ Failed: {response.error}")
    
    # =========================================================================
    # Polling Commands
    # =========================================================================
    
    def do_poll(self, arg):
        """Start polling for new communications.
        
        Usage: poll [interval]
        
        Continuously polls for new comms and plays audio.
        Default interval is 2 seconds.
        """
        if not self._check_connected():
            return
        
        if self._polling:
            print("Already polling. Use 'stop' to stop.")
            return
        
        interval = float(arg) if arg else 2.0
        self._poll_interval = max(0.5, min(30.0, interval))
        
        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        
        print(f"Started polling every {self._poll_interval}s")
        print("Use 'stop' to stop polling.")
    
    def do_stop(self, arg):
        """Stop polling for communications."""
        self.do_stop_poll(arg)
    
    def do_stop_poll(self, arg):
        """Stop the polling loop."""
        if not self._polling:
            print("Not currently polling.")
            return
        
        self._polling = False
        if self._poll_thread:
            self._poll_thread.join(timeout=3.0)
        
        print("Polling stopped.")
    
    def _poll_loop(self):
        """Background polling loop."""
        logger.info("Poll loop started")
        
        while self._polling:
            try:
                response = self.sapi.get_comms_history()
                
                if response.success:
                    entries: List[CommEntry] = response.data or []
                    
                    # Play any new audio
                    new_count = 0
                    for entry in entries:
                        if entry.atc_url:
                            comm_id = hash(entry.atc_url)
                            if comm_id not in self._played_comm_ids:
                                self._played_comm_ids.add(comm_id)
                                self.audio.queue_atc_audio(
                                    url=entry.atc_url,
                                    station_name=entry.station_name,
                                    frequency=entry.frequency,
                                    message=entry.outgoing_message
                                )
                                new_count += 1
                    
                    if new_count > 0:
                        logger.info(f"Queued {new_count} new audio")
                
            except Exception as e:
                logger.error(f"Poll error: {e}")
            
            # Sleep in small increments to allow quick shutdown
            for _ in range(int(self._poll_interval * 10)):
                if not self._polling:
                    break
                time.sleep(0.1)
        
        logger.info("Poll loop ended")
    
    # =========================================================================
    # Audio Commands
    # =========================================================================
    
    def do_volume(self, arg):
        """Set or show audio volume.
        
        Usage: volume [0-100]
        
        Without argument, shows current volume.
        """
        if not self.audio:
            print("Audio not initialized.")
            return
        
        if arg:
            try:
                vol = int(arg) / 100.0
                self.audio.set_volume(vol)
                print(f"Volume set to {int(vol * 100)}%")
            except ValueError:
                print("Usage: volume [0-100]")
        else:
            vol = self.audio.get_volume()
            print(f"Volume: {int(vol * 100)}%")
    
    def do_pause(self, arg):
        """Pause audio playback."""
        if self.audio:
            self.audio.pause()
            print("Audio paused.")
    
    def do_resume(self, arg):
        """Resume audio playback."""
        if self.audio:
            self.audio.play()
            print("Audio resumed.")
    
    def do_skip(self, arg):
        """Skip current audio."""
        if self.audio:
            self.audio.skip()
            print("Skipped.")
    
    def do_stop_audio(self, arg):
        """Stop audio and clear queue."""
        if self.audio:
            self.audio.stop()
            print("Audio stopped.")
    
    def do_clear_played(self, arg):
        """Clear the list of played audio (allows replay)."""
        self._played_comm_ids.clear()
        print("Cleared played audio list. Audio can be re-played.")
    
    # =========================================================================
    # Weather Commands
    # =========================================================================
    
    def do_weather(self, arg):
        """Get weather for an airport.
        
        Usage: weather <ICAO>
        
        Example: weather KTRK
        """
        if not self._check_connected():
            return
        
        if not arg:
            print("Usage: weather <ICAO>")
            return
        
        icao = arg.upper().strip()
        response = self.sapi.get_weather(icao)
        
        if response.success:
            wx = response.data
            print(f"\n{'='*60}")
            print(f"Weather for {wx.icao}")
            print(f"{'='*60}")
            print(f"\nMETAR: {wx.metar}")
            print(f"\nTAF: {wx.taf}")
            if wx.atis:
                print(f"\nATIS: {wx.atis}")
        else:
            print(f"✗ Failed: {response.error}")
    
    # =========================================================================
    # Utility Commands
    # =========================================================================
    
    def do_clear(self, arg):
        """Clear the screen."""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def do_quit(self, arg):
        """Exit the CLI."""
        return self._shutdown()
    
    def do_exit(self, arg):
        """Exit the CLI."""
        return self._shutdown()
    
    def do_EOF(self, arg):
        """Handle Ctrl+D."""
        print()  # Newline
        return self._shutdown()
    
    def _shutdown(self):
        """Clean shutdown."""
        print("Shutting down...")
        
        if self._polling:
            self._polling = False
            if self._poll_thread:
                self._poll_thread.join(timeout=2.0)
        
        if self.audio:
            self.audio.shutdown()
        
        return True
    
    def _check_connected(self) -> bool:
        """Check if connected and show message if not."""
        if not self.sapi or not self.sapi.is_connected:
            print("Not connected. Use 'connect' first.")
            return False
        return True
    
    def default(self, line):
        """Handle unknown commands."""
        print(f"Unknown command: {line}")
        print("Type 'help' for available commands.")
    
    def emptyline(self):
        """Handle empty input (don't repeat last command)."""
        pass


def run_cli(args):
    """Run in interactive CLI mode."""
    cli = StratusCLI(config_path=args.config)
    
    # Auto-connect if requested
    if args.auto_connect:
        cli.preloop()
        cli.do_connect("")
    
    try:
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n")
        cli._shutdown()


def run_oneshot(args):
    """Run a single command and exit."""
    # Initialize
    sapi = SapiService(config_path=args.config)
    audio = AudioHandler()
    
    if not sapi.connect():
        print("Failed to connect to SAPI")
        sys.exit(1)
    
    if args.status:
        print(f"Status: {sapi.get_status()}")
        
    elif args.history:
        response = sapi.get_comms_history()
        if response.success:
            for entry in response.data:
                has_audio = "🔊" if entry.atc_url else "  "
                print(f"{has_audio} [{entry.frequency}] {entry.station_name}")
                if entry.outgoing_message:
                    print(f"   ATC: {entry.outgoing_message}")
        else:
            print(f"Error: {response.error}")
            
    elif args.play:
        response = sapi.get_comms_history()
        if response.success:
            queued = 0
            for entry in response.data:
                if entry.atc_url:
                    audio.queue_atc_audio(
                        url=entry.atc_url,
                        station_name=entry.station_name,
                        frequency=entry.frequency,
                        message=entry.outgoing_message
                    )
                    queued += 1
            
            if queued > 0:
                print(f"Playing {queued} audio files...")
                # Wait for playback to complete
                while audio.queue_size > 0 or audio.is_playing:
                    time.sleep(0.5)
        else:
            print(f"Error: {response.error}")
            
    elif args.say:
        response = sapi.say_as(args.say)
        if response.success:
            print("Transmission sent")
        else:
            print(f"Error: {response.error}")
    
    audio.shutdown()


def main():
    parser = argparse.ArgumentParser(
        description='StratusATC CLI Client',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python cli.py                        Start interactive mode
    python cli.py -c                     Start and auto-connect
    python cli.py --status               Check connection status
    python cli.py --history              Show comms history
    python cli.py --play                 Play all audio from history
    python cli.py --say "Message"        Send a pilot transmission
"""
    )
    
    parser.add_argument('--config', '-C', 
                        help='Path to config.ini file')
    parser.add_argument('--auto-connect', '-c', action='store_true',
                        help='Auto-connect on startup')
    
    # One-shot commands
    parser.add_argument('--status', '-s', action='store_true',
                        help='Check connection status and exit')
    parser.add_argument('--history', '-H', action='store_true',
                        help='Fetch and display comms history')
    parser.add_argument('--play', '-p', action='store_true',
                        help='Fetch history and play audio')
    parser.add_argument('--say', '-S', metavar='MESSAGE',
                        help='Send a pilot transmission')
    
    args = parser.parse_args()
    
    # Check if running in one-shot mode
    if args.status or args.history or args.play or args.say:
        run_oneshot(args)
    else:
        run_cli(args)


if __name__ == "__main__":
    main()
