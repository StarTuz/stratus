"""
Squawk Code Handler

STRATUS-006: Process transponder codes and trigger appropriate ATC behavior.

Special Codes:
- 7500: Hijack
- 7600: Radio failure (NORDO)
- 7700: Emergency
- 1200: VFR (default)
- 0000: Standby/Off
"""

import re
import logging
from enum import Enum, auto
from typing import Optional, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class SquawkType(Enum):
    """Classification of transponder codes."""
    NORMAL = auto()      # Standard assigned code
    VFR = auto()         # 1200 - VFR
    STANDBY = auto()     # 0000 or transponder off
    HIJACK = auto()      # 7500
    NORDO = auto()       # 7600 - Radio failure
    EMERGENCY = auto()   # 7700


@dataclass
class SquawkInfo:
    """Information about a squawk code."""
    code: str
    type: SquawkType
    description: str
    is_emergency: bool
    atc_response_required: bool


# Emergency code definitions
EMERGENCY_CODES = {
    "7500": SquawkInfo(
        code="7500",
        type=SquawkType.HIJACK,
        description="Hijack",
        is_emergency=True,
        atc_response_required=True
    ),
    "7600": SquawkInfo(
        code="7600",
        type=SquawkType.NORDO,
        description="Radio failure - NORDO",
        is_emergency=True,
        atc_response_required=False  # Can't respond if radio failed
    ),
    "7700": SquawkInfo(
        code="7700",
        type=SquawkType.EMERGENCY,
        description="General emergency",
        is_emergency=True,
        atc_response_required=True
    ),
}

# Special non-emergency codes
SPECIAL_CODES = {
    "1200": SquawkInfo(
        code="1200",
        type=SquawkType.VFR,
        description="VFR",
        is_emergency=False,
        atc_response_required=False
    ),
    "0000": SquawkInfo(
        code="0000",
        type=SquawkType.STANDBY,
        description="Standby",
        is_emergency=False,
        atc_response_required=False
    ),
}


class SquawkHandler:
    """
    Handle transponder code processing and emergency detection.
    """
    
    def __init__(self):
        self._current_code: str = "1200"  # Default VFR
        self._last_emergency: Optional[SquawkInfo] = None
        self._assigned_code: Optional[str] = None  # ATC-assigned code
    
    @property
    def current_code(self) -> str:
        return self._current_code
    
    @property
    def is_emergency(self) -> bool:
        return self._current_code in EMERGENCY_CODES
    
    def update(self, code: str) -> Optional[SquawkInfo]:
        """
        Update the current squawk code.
        
        Returns SquawkInfo if the code is special/emergency, None otherwise.
        """
        # Normalize code to 4 digits
        code = self._normalize_code(code)
        
        if code == self._current_code:
            return None  # No change
        
        old_code = self._current_code
        self._current_code = code
        
        # Check for emergency codes
        if code in EMERGENCY_CODES:
            info = EMERGENCY_CODES[code]
            self._last_emergency = info
            logger.warning(f"[SQUAWK] Emergency code activated: {code} ({info.description})")
            return info
        
        # Check for special codes
        if code in SPECIAL_CODES:
            info = SPECIAL_CODES[code]
            logger.info(f"[SQUAWK] Special code set: {code} ({info.description})")
            return info
        
        # Normal code
        logger.info(f"[SQUAWK] Code changed: {old_code} → {code}")
        return None
    
    def _normalize_code(self, code: str) -> str:
        """Normalize squawk code to 4-digit string."""
        # Extract digits only
        digits = re.sub(r"[^0-7]", "", str(code))
        
        # Pad to 4 digits
        return digits.zfill(4)[:4]
    
    def validate_code(self, code: str) -> Tuple[bool, str]:
        """
        Validate a squawk code.
        
        Squawk codes are octal (0-7 only).
        
        Returns:
            (is_valid, error_message)
        """
        code = str(code).strip()
        
        if len(code) != 4:
            return False, f"Squawk must be 4 digits, got {len(code)}"
        
        if not code.isdigit():
            return False, "Squawk must be numeric"
        
        # Check for invalid octal digits (8, 9)
        if any(d in code for d in "89"):
            return False, "Squawk codes are octal (0-7 only)"
        
        return True, ""
    
    def set_assigned_code(self, code: str):
        """Set the ATC-assigned squawk code."""
        valid, error = self.validate_code(code)
        if valid:
            self._assigned_code = self._normalize_code(code)
            logger.info(f"[SQUAWK] ATC assigned code: {self._assigned_code}")
        else:
            logger.warning(f"[SQUAWK] Invalid assigned code '{code}': {error}")
    
    def get_assigned_code(self) -> Optional[str]:
        """Get the ATC-assigned code, if any."""
        return self._assigned_code
    
    def generate_atc_response(self, pilot_callsign: str) -> Optional[str]:
        """
        Generate appropriate ATC response for current squawk state.
        
        Used when we need to acknowledge an emergency squawk.
        """
        if self._current_code == "7700":
            return f"{pilot_callsign}, I see you squawking emergency. Say nature of emergency."
        elif self._current_code == "7600":
            return f"{pilot_callsign}, if you read, squawk ident. No voice communication required."
        elif self._current_code == "7500":
            # 7500 - ATC will acknowledge without alerting hijacker
            return f"{pilot_callsign}, roger, squawk confirmed."
        
        return None
    
    def parse_squawk_from_atc(self, atc_message: str) -> Optional[str]:
        """
        Parse a squawk code from an ATC instruction.
        
        Examples:
            "Squawk 4512" → "4512"
            "Squawk VFR" → "1200"
            "Squawk seven-six-zero-zero" → "7600"
        """
        message_lower = atc_message.lower()
        
        # Check for VFR
        if "squawk vfr" in message_lower:
            return "1200"
        
        # Check for ident only
        if "squawk ident" in message_lower and "squawk" not in message_lower.replace("squawk ident", ""):
            return None  # Just ident, no code change
        
        # Look for numeric code
        match = re.search(r"squawk\s+(\d{4})", message_lower)
        if match:
            return match.group(1)
        
        # Look for spoken digits (e.g., "four five one two")
        spoken_pattern = r"squawk\s+(zero|one|two|three|four|five|six|seven|oh)[\s-]*(zero|one|two|three|four|five|six|seven|oh)[\s-]*(zero|one|two|three|four|five|six|seven|oh)[\s-]*(zero|one|two|three|four|five|six|seven|oh)"
        match = re.search(spoken_pattern, message_lower)
        if match:
            word_to_digit = {
                "zero": "0", "oh": "0",
                "one": "1", "two": "2", "three": "3", "four": "4",
                "five": "5", "six": "6", "seven": "7"
            }
            code = "".join(word_to_digit.get(w, "0") for w in match.groups())
            return code
        
        return None
    
    def get_atc_context(self) -> str:
        """Get squawk state for ATC prompt context."""
        if self._current_code in EMERGENCY_CODES:
            info = EMERGENCY_CODES[self._current_code]
            return f"TRANSPONDER: {self._current_code} - ⚠️ {info.description.upper()}"
        elif self._current_code in SPECIAL_CODES:
            info = SPECIAL_CODES[self._current_code]
            return f"TRANSPONDER: {self._current_code} ({info.description})"
        else:
            return f"TRANSPONDER: {self._current_code}"


# Global handler instance
_handler: Optional[SquawkHandler] = None


def get_squawk_handler() -> SquawkHandler:
    """Get the global squawk handler instance."""
    global _handler
    if _handler is None:
        _handler = SquawkHandler()
    return _handler
