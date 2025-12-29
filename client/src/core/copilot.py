"""
StratusML Copilot Module

Provides AI copilot functionality that automatically handles ATC communications:
- Parses ATC messages for frequency changes and auto-tunes
- Detects squawk code assignments and sets transponder
- Manages copilot mode state

This mirrors the official Stratus.AI copilot feature.
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional, Callable, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class CopilotMode(Enum):
    """Copilot operating modes."""
    OFF = "off"           # Pilot handles all comms
    MONITOR = "monitor"   # Copilot listens but doesn't respond
    FULL = "full"         # Copilot handles all routine comms


@dataclass
class FrequencyInstruction:
    """Parsed frequency change instruction from ATC."""
    frequency: str       # e.g., "125.400"
    facility: str        # e.g., "Approach", "Tower", "Center"
    channel: str         # COM1 or COM2 (default COM1)
    raw_text: str        # Original ATC text


@dataclass
class SquawkInstruction:
    """Parsed squawk code instruction from ATC."""
    code: str            # e.g., "4523"
    raw_text: str        # Original ATC text


@dataclass
class AltitudeInstruction:
    """Parsed altitude instruction from ATC."""
    altitude: int        # In feet
    instruction_type: str  # "climb", "descend", "maintain"
    raw_text: str


class Copilot:
    """
    AI Copilot that monitors and handles ATC communications.
    
    When enabled, the copilot will:
    - Parse incoming ATC messages for instructions
    - Auto-tune frequencies when ATC hands off
    - Set transponder codes when assigned
    - Can handle routine readbacks (via SAPI copilot entity)
    """
    
    # Regex patterns for parsing ATC messages
    FREQ_PATTERNS = [
        # "Contact approach on 125.400"
        r"contact\s+(\w+(?:\s+\w+)?)\s+(?:on\s+)?(\d{2,3}[\.\,]\d{1,3})",
        # "Frequency change approved, contact tower 118.700"
        r"contact\s+(\w+(?:\s+\w+)?)\s+(\d{2,3}[\.\,]\d{1,3})",
        # "Switch to departure 124.850"
        r"switch\s+(?:to\s+)?(\w+(?:\s+\w+)?)\s+(\d{2,3}[\.\,]\d{1,3})",
        # "Monitor ATIS on 127.250"
        r"monitor\s+(\w+)\s+(?:on\s+)?(\d{2,3}[\.\,]\d{1,3})",
        # "Change to 121.500" (generic)
        r"change\s+(?:to\s+)?(\w+)?\s*(\d{2,3}[\.\,]\d{1,3})",
    ]
    
    SQUAWK_PATTERNS = [
        # "Squawk 4523"
        r"squawk\s+(\d{4})",
        # "Transponder 1200"
        r"transponder\s+(\d{4})",
        # "Code 7700" (emergency)
        r"code\s+(\d{4})",
    ]
    
    ALTITUDE_PATTERNS = [
        # "Climb and maintain flight level 350" or "Climb and maintain 10,000"
        r"climb\s+(?:and\s+)?maintain\s+(?:flight\s+level\s+)?(\d[\d,]*)",
        # "Descend and maintain 5000"
        r"descend\s+(?:and\s+)?maintain\s+(?:flight\s+level\s+)?(\d[\d,]*)",
        # "Maintain 8000"
        r"maintain\s+(?:flight\s+level\s+)?(\d[\d,]*)",
    ]
    
    def __init__(self):
        self.mode = CopilotMode.OFF
        self._enabled = False
        
        # Callbacks for actions
        self.on_frequency_change: Optional[Callable[[str, str], None]] = None  # freq, channel
        self.on_squawk_change: Optional[Callable[[str], None]] = None  # code
        self.on_instruction_detected: Optional[Callable[[str], None]] = None  # description
        
        # Compile regex patterns
        self._freq_patterns = [re.compile(p, re.IGNORECASE) for p in self.FREQ_PATTERNS]
        self._squawk_patterns = [re.compile(p, re.IGNORECASE) for p in self.SQUAWK_PATTERNS]
        self._altitude_patterns = [re.compile(p, re.IGNORECASE) for p in self.ALTITUDE_PATTERNS]
        
        logger.info("Copilot initialized")
    
    @property
    def enabled(self) -> bool:
        """Check if copilot is enabled."""
        return self._enabled and self.mode != CopilotMode.OFF
    
    def enable(self, mode: CopilotMode = CopilotMode.FULL):
        """Enable copilot with specified mode."""
        self._enabled = True
        self.mode = mode
        logger.info(f"Copilot enabled in {mode.value} mode")
    
    def disable(self):
        """Disable copilot."""
        self._enabled = False
        self.mode = CopilotMode.OFF
        logger.info("Copilot disabled")
    
    def toggle(self) -> bool:
        """Toggle copilot on/off. Returns new state."""
        if self._enabled:
            self.disable()
        else:
            self.enable(CopilotMode.FULL)
        return self._enabled
    
    def process_atc_message(self, message: str, station: str = "") -> List[str]:
        """
        Process an ATC message and extract instructions.
        
        If copilot mode is FULL, will automatically execute actions.
        If mode is MONITOR, will only detect and report.
        
        Args:
            message: The ATC message text
            station: The ATC station name (for context)
            
        Returns:
            List of action descriptions taken or detected
        """
        if not self._enabled:
            return []
        
        actions = []
        
        # Check for frequency changes
        freq_instruction = self._parse_frequency(message)
        if freq_instruction:
            action = f"Frequency: {freq_instruction.facility} on {freq_instruction.frequency}"
            actions.append(action)
            
            if self.mode == CopilotMode.FULL and self.on_frequency_change:
                logger.info(f"Copilot auto-tuning: {freq_instruction.frequency}")
                self.on_frequency_change(freq_instruction.frequency, freq_instruction.channel)
                if self.on_instruction_detected:
                    self.on_instruction_detected(f"Auto-tuned to {freq_instruction.frequency}")
        
        # Check for squawk codes
        squawk_instruction = self._parse_squawk(message)
        if squawk_instruction:
            action = f"Squawk: {squawk_instruction.code}"
            actions.append(action)
            
            if self.mode == CopilotMode.FULL and self.on_squawk_change:
                logger.info(f"Copilot setting squawk: {squawk_instruction.code}")
                self.on_squawk_change(squawk_instruction.code)
                if self.on_instruction_detected:
                    self.on_instruction_detected(f"Set squawk {squawk_instruction.code}")
        
        # Check for altitude changes (just detect, don't act on autopilot)
        altitude_instruction = self._parse_altitude(message)
        if altitude_instruction:
            action = f"Altitude: {altitude_instruction.instruction_type} {altitude_instruction.altitude}ft"
            actions.append(action)
            
            if self.on_instruction_detected:
                self.on_instruction_detected(action)
        
        return actions
    
    def _parse_frequency(self, message: str) -> Optional[FrequencyInstruction]:
        """Parse message for frequency change instructions."""
        for pattern in self._freq_patterns:
            match = pattern.search(message)
            if match:
                groups = match.groups()
                facility = groups[0] if groups[0] else "ATC"
                # Handle frequency - could be in group 1 or 2 depending on pattern
                freq = groups[1] if len(groups) > 1 and groups[1] else groups[0]
                
                # Normalize frequency format (replace comma with period)
                freq = freq.replace(",", ".")
                
                # Validate it looks like a frequency (not the facility name)
                if re.match(r"\d{2,3}\.\d{1,3}", freq):
                    return FrequencyInstruction(
                        frequency=freq,
                        facility=facility.title() if facility else "ATC",
                        channel="COM1",  # Default to COM1
                        raw_text=match.group(0)
                    )
        return None
    
    def _parse_squawk(self, message: str) -> Optional[SquawkInstruction]:
        """Parse message for squawk code instructions."""
        for pattern in self._squawk_patterns:
            match = pattern.search(message)
            if match:
                code = match.group(1)
                # Validate squawk code (0000-7777, only 0-7 digits)
                if all(c in '01234567' for c in code):
                    return SquawkInstruction(
                        code=code,
                        raw_text=match.group(0)
                    )
        return None
    
    def _parse_altitude(self, message: str) -> Optional[AltitudeInstruction]:
        """Parse message for altitude instructions."""
        for pattern in self._altitude_patterns:
            match = pattern.search(message)
            if match:
                # Determine instruction type
                text = match.group(0).lower()
                if "climb" in text:
                    instr_type = "climb to"
                elif "descend" in text:
                    instr_type = "descend to"
                else:
                    instr_type = "maintain"
                
                # Parse altitude
                alt_str = match.group(1).replace(",", "")
                try:
                    altitude = int(alt_str)
                    # Handle flight levels (FL350 = 35000ft)
                    if altitude < 1000 and "flight level" in text.lower():
                        altitude *= 100
                    
                    return AltitudeInstruction(
                        altitude=altitude,
                        instruction_type=instr_type,
                        raw_text=match.group(0)
                    )
                except ValueError:
                    pass
        return None
    
    def get_status(self) -> dict:
        """Get current copilot status."""
        return {
            "enabled": self._enabled,
            "mode": self.mode.value,
            "mode_display": self._get_mode_display()
        }
    
    def _get_mode_display(self) -> str:
        """Get human-readable mode display."""
        if not self._enabled:
            return "OFF"
        return {
            CopilotMode.OFF: "OFF",
            CopilotMode.MONITOR: "MONITOR",
            CopilotMode.FULL: "ACTIVE"
        }.get(self.mode, "OFF")


# Singleton instance
_copilot: Optional[Copilot] = None


def get_copilot() -> Copilot:
    """Get the global copilot instance."""
    global _copilot
    if _copilot is None:
        _copilot = Copilot()
    return _copilot
