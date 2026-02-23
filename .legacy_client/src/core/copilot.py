
import re
import logging
from typing import List, Optional

from .squawk import get_squawk_handler

logger = logging.getLogger(__name__)

class CoPilot:
    """
    AI Co-pilot that parses ATC instructions and automates simulator actions.
    Functions as an 'Action Layer' between the Brain and the Simulator.
    
    STRATUS-006: Enhanced with SquawkHandler integration.
    """
    def __init__(self, sim_data):
        self.sim_data = sim_data
        self.enabled = False
        self.squawk_handler = get_squawk_handler()

    def set_enabled(self, enabled: bool):
        """Enable or disable the co-pilot automation."""
        self.enabled = enabled
        logger.info(f"Co-pilot {'enabled' if enabled else 'disabled'}")

    def process_atc_instruction(self, text: str) -> List[str]:
        """
        Parse ATC text and execute corresponding commands if enabled.
        Returns a list of actions taken for logging/display.
        
        Args:
            text: The full text response from the ATC AI.
            
        Returns:
            List[str]: Description of actions taken (e.g. "Tuned COM1 to 119.5")
        """
        if not self.enabled:
            return []

        actions_taken = []
        
        # 1. Parse Frequencies
        # Regex looks for patterns like "118.5", "121.500", "135.25"
        # Bounded by 118.0 and 137.0 (Civil Aviation Band)
        freq_matches = re.finditer(r'\b(1[1-3]\d\.\d{1,3})\b', text)
        
        for match in freq_matches:
            freq_str = match.group(1)
            try:
                f_val = float(freq_str)
                # Filter for valid COMM band (118.000 - 136.975)
                if 118.0 <= f_val < 137.0:
                    self.sim_data.set_com1_active(freq_str)
                    action = f"Tuned COM1 to {freq_str}"
                    if action not in actions_taken:
                        actions_taken.append(action)
                        logger.info(f"Co-pilot: {action}")
            except ValueError:
                continue

        # 2. Parse Squawk Codes using SquawkHandler (STRATUS-006)
        squawk_code = self.squawk_handler.parse_squawk_from_atc(text)
        
        if squawk_code:
            valid, error = self.squawk_handler.validate_code(squawk_code)
            
            if valid:
                # Set in simulator
                self.sim_data.set_transponder_code(squawk_code)
                
                # Track in handler
                self.squawk_handler.set_assigned_code(squawk_code)
                
                action = f"Set Transponder to {squawk_code}"
                actions_taken.append(action)
                logger.info(f"Co-pilot: {action}")
            else:
                logger.warning(f"Co-pilot: Ignored invalid squawk '{squawk_code}': {error}")
            
        return actions_taken

    def check_emergency_squawk(self) -> Optional[str]:
        """
        Check if current transponder is set to an emergency code.
        
        STRATUS-006: Returns emergency message if detected.
        
        Returns:
            Emergency description or None if normal
        """
        # Read current transponder from sim
        telemetry = self.sim_data.read_telemetry()
        if telemetry and hasattr(telemetry, 'transponder'):
            code = telemetry.transponder.code
            info = self.squawk_handler.update(code)
            
            if info and info.is_emergency:
                return info.description
        
        return None

    def get_squawk_context(self) -> str:
        """Get squawk state for ATC prompt context."""
        return self.squawk_handler.get_atc_context()

