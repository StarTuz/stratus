
import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class CoPilot:
    """
    AI Co-pilot that parses ATC instructions and automates simulator actions.
    Functions as an 'Action Layer' between the Brain and the Simulator.
    """
    def __init__(self, sim_data):
        self.sim_data = sim_data
        self.enabled = False

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
                # Also ignore 121.5 (Guard) as a generic command unless explicit?
                # For now, allow it.
                if 118.0 <= f_val < 137.0:
                    # HEURISTIC: Parsing context is hard. 
                    # If ATC mentions a frequency, they usually want you to switch to it.
                    # We will set COM1 Active.
                    # In future, we could check "contact... on" vs "monitor".
                    
                    # Prevent redundant tuning if already active
                    current_telemetry = self.sim_data.read_telemetry()
                    # Fuzzy match? String match is safer for now.
                    # Note: telemetry.com1.active might be "118.50" and freq_str "118.5"
                    
                    self.sim_data.set_com1_active(freq_str)
                    action = f"Tuned COM1 to {freq_str}"
                    if action not in actions_taken: # Dedup
                        actions_taken.append(action)
                        logger.info(f"Co-pilot: {action}")
            except ValueError:
                continue

        # 2. Parse Squawk Codes
        # "Squawk 4521", "Squawk code 0421"
        # Avoid years (2024) or altitudes (3000) by requiring "Squawk" keyword
        squawk_match = re.search(r'\bSquawk\s+(?:code\s+)?(\d{4})\b', text, re.IGNORECASE)
        
        if squawk_match:
            code = squawk_match.group(1)
            
            # Additional validation: Squawk codes are octal (0-7 only)
            if all(c in '01234567' for c in code):
                self.sim_data.set_transponder_code(code)
                action = f"Set Transponder to {code}"
                actions_taken.append(action)
                logger.info(f"Co-pilot: {action}")
            else:
                logger.warning(f"Co-pilot: Ignored invalid non-octal squawk code {code}")
            
        return actions_taken
