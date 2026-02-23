"""
Phraseology Feedback Scoring for Stratus ATC

Parses pilot readbacks and scores correctness for training value.
Provides feedback on missed elements and incorrect phraseology.

This is unique training value that no competitor offers.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class ReadbackElement(Enum):
    """Elements that require readback."""
    HOLD_SHORT = "hold_short"
    RUNWAY = "runway"
    SQUAWK = "squawk"
    FREQUENCY = "frequency"
    ALTITUDE = "altitude"
    HEADING = "heading"
    CALLSIGN = "callsign"


@dataclass
class ReadbackRequirement:
    """A single element requiring readback."""
    element_type: ReadbackElement
    original_value: str
    pattern: str  # Regex pattern to match in readback


@dataclass
class ReadbackScore:
    """Scoring result for a pilot readback."""
    score: int  # 0-100
    max_score: int = 100
    matched_elements: List[str] = field(default_factory=list)
    missed_elements: List[str] = field(default_factory=list)
    incorrect_elements: List[Tuple[str, str, str]] = field(default_factory=list)  # (element, expected, got)
    feedback: List[str] = field(default_factory=list)
    is_complete: bool = False


# Regex patterns for extracting readback requirements from ATC instructions
PATTERNS = {
    ReadbackElement.HOLD_SHORT: r'hold short(?:\s+(?:of\s+)?)?(?:runway\s+)?(\d+[LCR]?)',
    ReadbackElement.RUNWAY: r'runway\s+(\d+[LCR]?)',
    ReadbackElement.SQUAWK: r'squawk\s+(\d{4})',
    ReadbackElement.FREQUENCY: r'(?:contact|monitor|frequency)\s+[\w\s]+(?:on\s+)?(\d{3}\.\d{1,3})',
    ReadbackElement.ALTITUDE: r'(?:altitude|climb|descend|maintain)\s+(?:and maintain\s+)?(\d{1,5})',
    ReadbackElement.HEADING: r'heading\s+(\d{3})',
}


def extract_readback_requirements(atc_instruction: str) -> List[ReadbackRequirement]:
    """
    Extract elements from ATC instruction that require pilot readback.
    
    Args:
        atc_instruction: The ATC instruction text
        
    Returns:
        List of ReadbackRequirement objects
    """
    requirements = []
    instruction_lower = atc_instruction.lower()
    
    for element_type, pattern in PATTERNS.items():
        matches = re.finditer(pattern, instruction_lower)
        for match in matches:
            value = match.group(1) if match.lastindex else match.group(0)
            requirements.append(ReadbackRequirement(
                element_type=element_type,
                original_value=value.upper() if value else "",
                pattern=pattern,
            ))
    
    return requirements


def score_readback(
    atc_instruction: str,
    pilot_readback: str,
    require_callsign: bool = False,
    callsign: Optional[str] = None,
) -> ReadbackScore:
    """
    Score a pilot's readback against the ATC instruction.
    
    Args:
        atc_instruction: The ATC instruction to read back
        pilot_readback: The pilot's readback
        require_callsign: Whether callsign must be included
        callsign: The aircraft callsign (for verification)
        
    Returns:
        ReadbackScore with score and feedback
    """
    requirements = extract_readback_requirements(atc_instruction)
    
    if not requirements:
        # Nothing to read back
        return ReadbackScore(
            score=100,
            is_complete=True,
            feedback=["No critical readback elements detected."],
        )
    
    readback_lower = pilot_readback.lower()
    matched = []
    missed = []
    incorrect = []
    feedback = []
    
    # Check each requirement
    for req in requirements:
        expected = req.original_value.lower()
        
        # Build pattern to find this element in readback
        if req.element_type == ReadbackElement.HOLD_SHORT:
            # Must explicitly say "hold short"
            if "hold short" in readback_lower and expected in readback_lower:
                matched.append(f"Hold short {expected.upper()}")
            elif "hold short" in readback_lower:
                matched.append(f"Hold short (runway unclear)")
            else:
                missed.append(f"Hold short {expected.upper()}")
                feedback.append(f"⚠️ CRITICAL: You must read back 'hold short of runway {expected.upper()}'")
        
        elif req.element_type == ReadbackElement.RUNWAY:
            # Check runway number is in readback
            if expected in readback_lower:
                matched.append(f"Runway {expected.upper()}")
            else:
                # Check if any runway number is said (might be wrong one)
                runway_match = re.search(r'runway\s+(\d+[lcr]?)', readback_lower)
                if runway_match:
                    got = runway_match.group(1)
                    if got != expected:
                        incorrect.append(("Runway", expected.upper(), got.upper()))
                        feedback.append(f"❌ Wrong runway: said '{got.upper()}', should be '{expected.upper()}'")
                else:
                    missed.append(f"Runway {expected.upper()}")
                    feedback.append(f"Missing runway assignment: '{expected.upper()}'")
        
        elif req.element_type == ReadbackElement.SQUAWK:
            # Squawk codes must be exact
            if expected in readback_lower:
                matched.append(f"Squawk {expected}")
            else:
                squawk_match = re.search(r'squawk\s+(\d{4})', readback_lower)
                if squawk_match:
                    got = squawk_match.group(1)
                    if got != expected:
                        incorrect.append(("Squawk", expected, got))
                        feedback.append(f"❌ Wrong squawk: said '{got}', assigned '{expected}'")
                else:
                    missed.append(f"Squawk {expected}")
                    feedback.append(f"Missing squawk code readback: '{expected}'")
        
        elif req.element_type == ReadbackElement.FREQUENCY:
            # Frequency must be in readback
            if expected in readback_lower:
                matched.append(f"Frequency {expected}")
            else:
                freq_match = re.search(r'(\d{3}\.\d{1,3})', readback_lower)
                if freq_match:
                    got = freq_match.group(1)
                    # Normalize for comparison
                    if got.replace(".", "") != expected.replace(".", ""):
                        incorrect.append(("Frequency", expected, got))
                        feedback.append(f"❌ Wrong frequency: said '{got}', should be '{expected}'")
                    else:
                        matched.append(f"Frequency {expected}")
                else:
                    missed.append(f"Frequency {expected}")
                    feedback.append(f"Missing frequency readback: '{expected}'")
        
        elif req.element_type == ReadbackElement.ALTITUDE:
            # Altitude readback
            if expected in readback_lower:
                matched.append(f"Altitude {expected}")
            else:
                alt_match = re.search(r'(\d{1,5})\s*(?:feet|ft)?', readback_lower)
                if alt_match:
                    got = alt_match.group(1)
                    if got != expected:
                        incorrect.append(("Altitude", expected, got))
                        feedback.append(f"❌ Wrong altitude: said '{got}', should be '{expected}'")
                    else:
                        matched.append(f"Altitude {expected}")
                else:
                    missed.append(f"Altitude {expected}")
                    feedback.append(f"Missing altitude readback")
        
        elif req.element_type == ReadbackElement.HEADING:
            # Heading readback
            if expected in readback_lower:
                matched.append(f"Heading {expected}")
            else:
                hdg_match = re.search(r'heading\s+(\d{3})', readback_lower)
                if hdg_match:
                    got = hdg_match.group(1)
                    if got != expected:
                        incorrect.append(("Heading", expected, got))
                        feedback.append(f"❌ Wrong heading: said '{got}°', should be '{expected}°'")
                else:
                    missed.append(f"Heading {expected}")
                    feedback.append(f"Missing heading readback")
    
    # Check callsign if required
    if require_callsign and callsign:
        callsign_lower = callsign.lower()
        # Allow partial callsign (last 3 chars)
        short_callsign = callsign_lower[-3:] if len(callsign_lower) >= 3 else callsign_lower
        if callsign_lower in readback_lower or short_callsign in readback_lower:
            matched.append("Callsign")
        else:
            missed.append("Callsign")
            feedback.append("Missing callsign in readback")
    
    # Calculate score
    total_elements = len(requirements) + (1 if require_callsign and callsign else 0)
    if total_elements == 0:
        score = 100
    else:
        # Matched = full points, incorrect = half penalty, missed = full penalty
        points = len(matched)
        penalty = len(incorrect) * 0.5 + len(missed)
        score = max(0, int(100 * (points / total_elements) - (penalty / total_elements) * 50))
    
    is_complete = len(missed) == 0 and len(incorrect) == 0
    
    if is_complete:
        feedback.insert(0, "✅ Complete and correct readback!")
    elif score >= 80:
        feedback.insert(0, "Good readback, minor issues.")
    elif score >= 50:
        feedback.insert(0, "Partial readback - review requirements.")
    else:
        feedback.insert(0, "⚠️ Incomplete readback - controller may request repeat.")
    
    return ReadbackScore(
        score=score,
        max_score=100,
        matched_elements=matched,
        missed_elements=missed,
        incorrect_elements=incorrect,
        feedback=feedback,
        is_complete=is_complete,
    )


def generate_training_feedback(
    atc_instruction: str,
    pilot_readback: str,
    callsign: Optional[str] = None,
) -> str:
    """
    Generate human-readable training feedback for a readback.
    
    Args:
        atc_instruction: ATC instruction
        pilot_readback: Pilot readback
        callsign: Aircraft callsign
        
    Returns:
        Formatted feedback string
    """
    result = score_readback(
        atc_instruction,
        pilot_readback,
        require_callsign=True,
        callsign=callsign,
    )
    
    lines = [
        f"📊 Readback Score: {result.score}/{result.max_score}",
        "",
    ]
    
    if result.matched_elements:
        lines.append("✅ Correct:")
        for elem in result.matched_elements:
            lines.append(f"   • {elem}")
        lines.append("")
    
    if result.missed_elements:
        lines.append("❌ Missing:")
        for elem in result.missed_elements:
            lines.append(f"   • {elem}")
        lines.append("")
    
    if result.incorrect_elements:
        lines.append("⚠️ Incorrect:")
        for elem, expected, got in result.incorrect_elements:
            lines.append(f"   • {elem}: said '{got}', should be '{expected}'")
        lines.append("")
    
    if result.feedback:
        lines.append("💡 Feedback:")
        for fb in result.feedback:
            lines.append(f"   {fb}")
    
    return "\n".join(lines)


# Test cases
if __name__ == "__main__":
    print("=" * 60)
    print("Phraseology Feedback Scoring - Test Cases")
    print("=" * 60)
    
    test_cases = [
        # Perfect readback
        (
            "Cessna 12345, taxi to runway 28 via Alpha, hold short of runway 10",
            "Taxi runway 28 via Alpha, hold short runway 10, Cessna 12345",
            "N12345",
        ),
        # Missing hold short
        (
            "Cessna 12345, taxi to runway 28 via Alpha, hold short of runway 10",
            "Taxi runway 28 via Alpha, Cessna 345",
            "N12345",
        ),
        # Wrong runway
        (
            "Cessna 12345, cleared to land runway 28L",
            "Cleared to land runway 28R, 345",
            "N12345",
        ),
        # Perfect squawk and frequency
        (
            "Cessna 12345, squawk 4521, contact approach on 124.5",
            "Squawk 4521, approach on 124.5, 345",
            "N12345",
        ),
        # Wrong squawk
        (
            "Cessna 12345, squawk 4521",
            "Squawk 4512, 345",
            "N12345",
        ),
    ]
    
    for i, (atc, pilot, callsign) in enumerate(test_cases, 1):
        print(f"\n--- Test {i} ---")
        print(f"ATC: {atc}")
        print(f"Pilot: {pilot}")
        print()
        print(generate_training_feedback(atc, pilot, callsign))
        print()
