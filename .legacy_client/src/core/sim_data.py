"""
Sim Data Interface

Reads telemetry from X-Plane plugin and writes commands to control the sim.

Data files:
  ~/.local/share/StratusATC/stratus_telemetry.json  (plugin writes, we read)
  ~/.local/share/StratusATC/stratus_commands.json   (we write, plugin reads)
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import time

logger = logging.getLogger(__name__)


@dataclass
class RadioState:
    """State of a COM radio."""
    active: str = "---"
    standby: str = "---"
    active_hz: int = 0
    standby_hz: int = 0
    power: bool = False


@dataclass 
class TransponderState:
    """State of the transponder."""
    code: str = "1200"
    code_int: int = 1200
    mode: str = "STBY"
    mode_int: int = 1


@dataclass
class SimTelemetry:
    """Current state from the flight simulator."""
    # Position
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_msl: float = 0.0
    altitude_agl: float = 0.0
    heading_mag: float = 0.0
    heading_true: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    on_ground: bool = True
    
    # Speed
    ias: float = 0.0
    tas: float = 0.0
    groundspeed: float = 0.0
    vertical_speed: float = 0.0
    
    # Radios
    com1: RadioState = field(default_factory=RadioState)
    com2: RadioState = field(default_factory=RadioState)
    transponder: TransponderState = field(default_factory=TransponderState)
    
    tail_number: str = "UNKNOWN"
    icao_type: str = "C172"
    
    # Metadata
    timestamp: float = 0.0
    sim: str = "unknown"
    connected: bool = False
    stale: bool = True  # True if data is old (> 2 seconds)


class SimDataInterface:
    """
    Interface for reading telemetry and sending commands to the flight sim.
    
    Works via JSON files exchanged with the X-Plane plugin.
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the sim data interface.
        
        Args:
            data_dir: Override the data directory (default: ~/.local/share/StratusATC)
        """
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path.home() / ".local" / "share" / "StratusATC"
        
        self.telemetry_file = self.data_dir / "stratus_telemetry.json"
        self.commands_file = self.data_dir / "stratus_commands.json"
        self.comms_display_file = self.data_dir / "comms_display.json"
        
        self._last_telemetry: Optional[SimTelemetry] = None
        self._pending_commands: List[Dict[str, Any]] = []
        
        logger.info(f"SimDataInterface initialized. Data dir: {self.data_dir}")
    
    def write_comms_for_overlay(self, messages: List[Dict[str, Any]], connected: bool = True):
        """
        Write communications data for the in-sim overlay to display.
        
        Args:
            messages: List of message dicts with keys: station, message, timestamp, is_atc
            connected: Whether the SAPI is connected
        """
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            data = {
                "messages": messages[-3:],  # Only last 3 messages
                "connected": connected,
                "timestamp": time.time()
            }
            
            with open(self.comms_display_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error writing comms display: {e}")
    
    def read_telemetry(self) -> SimTelemetry:
        """
        Read current telemetry from the simulator.
        
        Returns:
            SimTelemetry object with current state
        """
        telemetry = SimTelemetry()
        
        if not self.telemetry_file.exists():
            telemetry.connected = False
            telemetry.stale = True
            return telemetry
        
        try:
            with open(self.telemetry_file, 'r') as f:
                data = json.load(f)
            
            # Check if data is stale (more than 2 seconds old)
            file_mtime = self.telemetry_file.stat().st_mtime
            age = time.time() - file_mtime
            telemetry.stale = age > 2.0
            telemetry.connected = not telemetry.stale
            
            # Parse position
            telemetry.latitude = data.get("latitude", 0.0)
            telemetry.longitude = data.get("longitude", 0.0)
            telemetry.altitude_msl = data.get("altitude_msl", 0.0)
            telemetry.altitude_agl = data.get("altitude_agl", 0.0)
            telemetry.heading_mag = data.get("heading_mag", 0.0)
            telemetry.heading_true = data.get("heading_true", 0.0)
            telemetry.pitch = data.get("pitch", 0.0)
            telemetry.roll = data.get("roll", 0.0)
            telemetry.on_ground = data.get("on_ground", True)
            
            # Parse speed
            telemetry.ias = data.get("ias", 0.0)
            telemetry.tas = data.get("tas", 0.0)
            telemetry.groundspeed = data.get("groundspeed", 0.0)
            telemetry.vertical_speed = data.get("vertical_speed", 0.0)
            
            # Parse COM1
            com1_data = data.get("com1", {})
            telemetry.com1 = RadioState(
                active=com1_data.get("active", "---"),
                standby=com1_data.get("standby", "---"),
                active_hz=com1_data.get("active_hz", 0),
                standby_hz=com1_data.get("standby_hz", 0),
                power=com1_data.get("power", False)
            )
            
            # Parse COM2
            com2_data = data.get("com2", {})
            telemetry.com2 = RadioState(
                active=com2_data.get("active", "---"),
                standby=com2_data.get("standby", "---"),
                active_hz=com2_data.get("active_hz", 0),
                standby_hz=com2_data.get("standby_hz", 0),
                power=com2_data.get("power", False)
            )
            
            # Parse transponder
            xpdr_data = data.get("transponder", {})
            telemetry.transponder = TransponderState(
                code=xpdr_data.get("code", "1200"),
                code_int=xpdr_data.get("code_int", 1200),
                mode=xpdr_data.get("mode", "STBY"),
                mode_int=xpdr_data.get("mode_int", 1)
            )
            
            # Aircraft Info
            telemetry.tail_number = data.get("tail_number", "UNKNOWN")
            telemetry.icao_type = data.get("icao_type", "C172")
            
            self._last_telemetry = telemetry
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid telemetry JSON: {e}")
            telemetry.connected = False
            telemetry.stale = True
        except Exception as e:
            logger.error(f"Error reading telemetry: {e}")
            telemetry.connected = False
            telemetry.stale = True
        
        return telemetry
    
    @property
    def is_sim_connected(self) -> bool:
        """Check if the simulator is connected (telemetry is fresh)."""
        telemetry = self.read_telemetry()
        return telemetry.connected and not telemetry.stale
    
    # =========================================================================
    # Command Methods
    # =========================================================================
    
    def _send_command(self, cmd: Dict[str, Any]):
        """Queue a command to be sent to the simulator."""
        self._pending_commands.append(cmd)
        self._flush_commands()
    
    def _flush_commands(self):
        """Write pending commands to the commands file."""
        if not self._pending_commands:
            return
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            command_data = {
                "commands": self._pending_commands,
                "timestamp": time.time()
            }
            
            with open(self.commands_file, 'w') as f:
                json.dump(command_data, f, indent=2)
            
            logger.debug(f"Sent {len(self._pending_commands)} commands to sim")
            self._pending_commands.clear()
            
        except Exception as e:
            logger.error(f"Error writing commands: {e}")
    
    def set_com1_active(self, frequency: str):
        """Set COM1 active frequency (e.g., '121.500')."""
        self._send_command({"type": "set_com1_active", "frequency": frequency})
        logger.info(f"Command: Set COM1 active to {frequency}")
    
    def set_com1_standby(self, frequency: str):
        """Set COM1 standby frequency."""
        self._send_command({"type": "set_com1_standby", "frequency": frequency})
        logger.info(f"Command: Set COM1 standby to {frequency}")
    
    def swap_com1(self):
        """Swap COM1 active and standby frequencies."""
        self._send_command({"type": "swap_com1"})
        logger.info("Command: Swap COM1")
    
    def set_com2_active(self, frequency: str):
        """Set COM2 active frequency."""
        self._send_command({"type": "set_com2_active", "frequency": frequency})
        logger.info(f"Command: Set COM2 active to {frequency}")
    
    def set_com2_standby(self, frequency: str):
        """Set COM2 standby frequency."""
        self._send_command({"type": "set_com2_standby", "frequency": frequency})
        logger.info(f"Command: Set COM2 standby to {frequency}")
    
    def swap_com2(self):
        """Swap COM2 active and standby frequencies."""
        self._send_command({"type": "swap_com2"})
        logger.info("Command: Swap COM2")
    
    def set_transponder_code(self, code: str):
        """Set transponder squawk code (e.g., '1200')."""
        self._send_command({"type": "set_transponder", "code": code})
        logger.info(f"Command: Set transponder to {code}")
    
    def set_transponder_mode(self, mode: str):
        """Set transponder mode ('OFF', 'STBY', 'ON', 'ALT')."""
        self._send_command({"type": "set_transponder_mode", "mode": mode})
        logger.info(f"Command: Set transponder mode to {mode}")
