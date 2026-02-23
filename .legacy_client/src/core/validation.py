"""
ATC Response Validation Module

STRATUS-003: Validate LLM responses before sending to TTS.

Catches:
- Prompt injection attempts
- Hallucinated values (impossible altitudes, invalid frequencies)
- Markup/code leakage
- Empty or malformed responses

Team Recommendation 3: Adds readback requirements and procedure validation.
"""

import re
import logging
from typing import Tuple, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of ATC response validation."""
    valid: bool
    cleaned_response: str
    issues: List[str]
    original_response: str
    warnings: List[str] = None  # Non-critical issues
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


# Patterns that should never appear in ATC responses
SUSPICIOUS_PATTERNS = [
    # Prompt injection markers
    (r"<\|.*?\|>", "LLM control token"),
    (r"\[INST\]", "Instruction marker"),
    (r"\[/INST\]", "Instruction marker"),
    (r"<<SYS>>", "System prompt marker"),
    (r"<</SYS>>", "System prompt marker"),
    (r"###\s*(Human|Assistant|System):", "Chat role marker"),
    
    # Code/markup leakage
    (r"```", "Code block"),
    (r"<script", "Script tag"),
    (r"function\s*\(", "JavaScript function"),
    (r"def\s+\w+\s*\(", "Python function"),
    
    # Obvious AI artifacts
    (r"As an AI", "AI self-reference"),
    (r"I'm an AI", "AI self-reference"),
    (r"language model", "AI self-reference"),
    (r"I cannot", "Refusal phrase"),
    (r"I'm sorry, but", "Apology phrase"),
]

# Prohibited phraseology (per FAA 7110.65 / AIM)
PROHIBITED_PHRASES = [
    (r"\bcleared to take\s*off\b", "Use 'cleared for takeoff' (Tower only)"),
    (r"\btaking off\b", "Use 'departing' instead"),
    (r"\bwith you\b", "Just state position, don't say 'with you'"),
    (r"\bback to you\b", "Use proper handoff phraseology"),
    (r"\baffirmative\b", "Use specific readback for clearances"),
    (r"\bthis is [A-Z]", "Don't say 'this is', start with callsign"),
    (r"\bany traffic.+advise\b", "Discouraged - use standard position reports instead"),
]

# Patterns that indicate out-of-scope IFR operations
IFR_SCOPE_VIOLATIONS = [
    (r"\bcleared.*ILS\b", "IFR approach - out of scope"),
    (r"\bcleared.*approach\b", "IFR approach - out of scope"),
    (r"\bcleared.*SID\b", "SID - out of scope"),
    (r"\bcleared.*STAR\b", "STAR - out of scope"),
    (r"\bhold as published\b", "Holding pattern - out of scope"),
    (r"\bexpect.*vectors\b", "IFR vectors - out of scope"),
    (r"\bcleared to.*via\b", "IFR routing - out of scope"),
]

# Realistic ATC value ranges
ATC_VALIDATION_RULES = {
    "altitude_max": 60000,      # FL600 max
    "altitude_min": -1000,      # Below sea level (Death Valley)
    "heading_max": 360,
    "heading_min": 0,
    "freq_min": 118.0,          # VHF air band starts
    "freq_max": 137.0,          # VHF air band ends
    "squawk_min": 0,
    "squawk_max": 7777,         # Octal max
}


def validate_atc_response(response: str) -> ValidationResult:
    """
    Validate an LLM-generated ATC response.
    
    Args:
        response: Raw response from LLM
        
    Returns:
        ValidationResult with validity, cleaned response, and issues found
    """
    if not response:
        return ValidationResult(
            valid=False,
            cleaned_response="",
            issues=["Empty response"],
            original_response=""
        )
    
    issues = []
    warnings = []
    cleaned = response.strip()
    original = cleaned
    
    # Check for suspicious patterns (critical)
    for pattern, description in SUSPICIOUS_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            issues.append(f"Contains {description}")
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    
    # Check for prohibited phraseology (warning)
    for pattern, description in PROHIBITED_PHRASES:
        if re.search(pattern, cleaned, re.IGNORECASE):
            warnings.append(f"Prohibited: {description}")
    
    # Check for IFR scope violations (warning but flag prominently)
    for pattern, description in IFR_SCOPE_VIOLATIONS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            warnings.append(f"SCOPE: {description}")
            logger.warning(f"[VALIDATION] Out of scope IFR content detected: {description}")
    
    # Check for unrealistic altitudes
    altitude_matches = re.findall(r"(\d{1,6})\s*(?:feet|ft|')", cleaned, re.IGNORECASE)
    for alt_str in altitude_matches:
        try:
            alt = int(alt_str)
            if alt > ATC_VALIDATION_RULES["altitude_max"]:
                issues.append(f"Unrealistic altitude: {alt}ft")
        except ValueError:
            pass
    
    # Check for unrealistic flight levels
    fl_matches = re.findall(r"FL\s*(\d{2,3})", cleaned, re.IGNORECASE)
    for fl_str in fl_matches:
        try:
            fl = int(fl_str) * 100  # FL350 = 35000ft
            if fl > ATC_VALIDATION_RULES["altitude_max"]:
                issues.append(f"Unrealistic flight level: FL{fl_str}")
        except ValueError:
            pass
    
    # Check for invalid frequencies
    freq_matches = re.findall(r"(\d{3}[.,]\d{1,3})", cleaned)
    for freq_str in freq_matches:
        try:
            freq = float(freq_str.replace(",", "."))
            if not (ATC_VALIDATION_RULES["freq_min"] <= freq <= ATC_VALIDATION_RULES["freq_max"]):
                if not (0 <= freq <= 7777):
                    issues.append(f"Invalid frequency: {freq_str}")
        except ValueError:
            pass
    
    # Check for invalid squawk codes
    squawk_matches = re.findall(r"squawk\s*(\d{4})", cleaned, re.IGNORECASE)
    for squawk_str in squawk_matches:
        try:
            if any(d in squawk_str for d in "89"):
                issues.append(f"Invalid squawk code (contains 8 or 9): {squawk_str}")
            elif int(squawk_str) > ATC_VALIDATION_RULES["squawk_max"]:
                issues.append(f"Invalid squawk code: {squawk_str}")
        except ValueError:
            pass
    
    # Validate taxi instructions have hold short (if mentions taxiway)
    if re.search(r"\btaxi\b.*\brunway\b", cleaned, re.IGNORECASE):
        if not re.search(r"hold short", cleaned, re.IGNORECASE):
            warnings.append("Taxi instruction should include 'hold short' when crossing runways")
    
    # Clean up whitespace and quotes
    cleaned = cleaned.strip()
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]
    if cleaned.startswith("'") and cleaned.endswith("'"):
        cleaned = cleaned[1:-1]
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Check minimum response length
    if len(cleaned) < 5:
        issues.append("Response too short")
    
    # Log issues if any
    if issues:
        logger.warning(f"[VALIDATION] Issues found: {issues}")
        logger.debug(f"[VALIDATION] Original: {original[:100]}...")
    if warnings:
        logger.info(f"[VALIDATION] Warnings: {warnings}")
    
    # Determine validity (allow minor issues but fail on critical ones)
    critical_issues = [i for i in issues if any(kw in i for kw in 
        ["LLM control", "System prompt", "Script tag", "Empty", "too short"])]
    
    return ValidationResult(
        valid=len(critical_issues) == 0,
        cleaned_response=cleaned if cleaned else "Say again",
        issues=issues,
        original_response=original,
        warnings=warnings
    )


def check_readback_required(atc_instruction: str) -> List[str]:
    """
    Check what elements in an ATC instruction require readback.
    
    Per FAA 7110.65 2-4-3, pilots MUST read back:
    - Hold short instructions
    - Runway assignments
    - Altimeter settings (IFR)
    - Frequency changes
    - Transponder codes
    
    Returns:
        List of elements that require readback
    """
    requires_readback = []
    
    # Hold short is mandatory
    if re.search(r"hold short", atc_instruction, re.IGNORECASE):
        match = re.search(r"hold short (?:of )?runway (\d+[LRC]?)", atc_instruction, re.IGNORECASE)
        if match:
            requires_readback.append(f"Hold short runway {match.group(1)}")
        else:
            requires_readback.append("Hold short instruction")
    
    # Runway assignments (takeoff/landing clearance)
    if re.search(r"cleared (?:for |to )?(?:takeoff|land|the option)", atc_instruction, re.IGNORECASE):
        match = re.search(r"runway (\d+[LRC]?)", atc_instruction, re.IGNORECASE)
        if match:
            requires_readback.append(f"Runway {match.group(1)}")
    
    # Frequency changes
    freq_match = re.search(r"(?:contact|monitor).*?(\d{3}\.\d{1,3})", atc_instruction, re.IGNORECASE)
    if freq_match:
        requires_readback.append(f"Frequency {freq_match.group(1)}")
    
    # Transponder codes
    squawk_match = re.search(r"squawk\s*(\d{4})", atc_instruction, re.IGNORECASE)
    if squawk_match:
        requires_readback.append(f"Squawk {squawk_match.group(1)}")
    
    return requires_readback


def get_fallback_response() -> str:
    """Get a safe fallback response when validation fails critically."""
    return "Stand by"


def sanitize_for_tts(text: str) -> str:
    """
    Clean text for TTS engine.
    
    Removes characters that may cause TTS issues.
    """
    text = re.sub(r'[<>{}[\]|\\^~`]', '', text)
    text = text.replace('"', '').replace("'", '')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def is_within_scope(response: str) -> Tuple[bool, str]:
    """
    Check if response is within VFR-only scope.
    
    Returns:
        (is_in_scope, reason) tuple
    """
    for pattern, description in IFR_SCOPE_VIOLATIONS:
        if re.search(pattern, response, re.IGNORECASE):
            return False, description
    return True, ""

