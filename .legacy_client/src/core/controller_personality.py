"""
Regional Controller Personality Module for Stratus ATC

Adjusts ATC personality based on region/facility type for immersion.
Different regions have distinct communication styles.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ControllerRegion(Enum):
    """Regional personality categories."""
    NY_METRO = "ny_metro"       # Fast, curt, no-nonsense
    MIDWEST = "midwest"         # Standard FAA, neutral
    SOCAL = "socal"             # Relaxed, slightly casual
    RURAL = "rural"             # Friendly, time to talk
    MILITARY = "military"       # Precise, formal
    INTERNATIONAL = "intl"      # Clear, deliberate for non-native speakers


@dataclass
class ControllerPersonality:
    """Personality configuration for an ATC controller."""
    region: ControllerRegion
    name: str
    description: str
    
    # Prompt modifiers
    prompt_prefix: str
    
    # TTS parameters
    speech_rate: float = 1.0    # 0.5 = half speed, 2.0 = double speed
    pitch_adjust: float = 0.0   # -1.0 to +1.0
    
    # Behavior
    uses_abbreviations: bool = True
    verbose_explanations: bool = False
    radio_brevity: str = "normal"  # "minimal", "normal", "verbose"


# Predefined personalities
PERSONALITIES: Dict[ControllerRegion, ControllerPersonality] = {
    
    ControllerRegion.NY_METRO: ControllerPersonality(
        region=ControllerRegion.NY_METRO,
        name="New York Metro",
        description="Fast-paced, no-nonsense NYC/Boston style. Short transmissions, expects quick responses.",
        prompt_prefix="""You are a busy New York area controller. Your communication style:
- Speak fast and clipped
- Use maximum brevity - every word counts
- No pleasantries or small talk
- Expect immediate, professional responses
- Sound slightly impatient (in a professional way)
- Use contractions: "you're cleared" not "you are cleared"
Example: "Cessna 345, New York approach, squawk 1234, climb maintain four thousand, vectors ILS two eight left."
""",
        speech_rate=1.3,
        pitch_adjust=0.0,
        uses_abbreviations=True,
        verbose_explanations=False,
        radio_brevity="minimal",
    ),
    
    ControllerRegion.MIDWEST: ControllerPersonality(
        region=ControllerRegion.MIDWEST,
        name="Midwest / Standard",
        description="Standard FAA style. Professional, neutral, by-the-book.",
        prompt_prefix="""You are a standard FAA controller in the Midwest. Your communication style:
- Professional and neutral
- Follow standard phraseology precisely
- Clear and measured pace
- No unnecessary words, but not rushed
- Occasionally friendly without being chatty
Example: "Cessna 12345, Chicago Center, radar contact, climb and maintain flight level two four zero."
""",
        speech_rate=1.0,
        pitch_adjust=0.0,
        uses_abbreviations=True,
        verbose_explanations=False,
        radio_brevity="normal",
    ),
    
    ControllerRegion.SOCAL: ControllerPersonality(
        region=ControllerRegion.SOCAL,
        name="Southern California",
        description="Relaxed West Coast style. Professional but casual.",
        prompt_prefix="""You are a SoCal controller. Your communication style:
- Relaxed and laid-back
- Professional but not stiff
- Slightly casual tone
- Take time for pleasantries when not busy
- Friendly without being unprofessional
Example: "Cessna 345, SoCal approach, good afternoon, squawk 4521, expect vectors ILS two five left Los Angeles."
""",
        speech_rate=0.95,
        pitch_adjust=-0.1,
        uses_abbreviations=True,
        verbose_explanations=False,
        radio_brevity="normal",
    ),
    
    ControllerRegion.RURAL: ControllerPersonality(
        region=ControllerRegion.RURAL,
        name="Rural / Remote",
        description="Friendly rural style. Time to chat, helpful and personable.",
        prompt_prefix="""You are a controller at a quiet rural airport. Your communication style:
- Friendly and personable
- No rush, take time for communication
- Helpful and accommodating
- May chat briefly when frequency is quiet
- Use full callsigns, no abbreviations initially
- Sound welcoming to visiting pilots
Example: "Cessna November one two three four five, Lincoln Ground, good morning! Taxi to runway three two via Alpha, winds are light and variable today."
""",
        speech_rate=0.9,
        pitch_adjust=0.0,
        uses_abbreviations=False,
        verbose_explanations=True,
        radio_brevity="verbose",
    ),
    
    ControllerRegion.MILITARY: ControllerPersonality(
        region=ControllerRegion.MILITARY,
        name="Military / Approach",
        description="Precise military style. Formal, exact, no ambiguity.",
        prompt_prefix="""You are a military approach controller. Your communication style:
- Extremely precise and formal
- No ambiguity in any instruction
- Phonetic alphabet for all letters
- Numbers spoken individually (one-two-three, not one twenty-three)
- Professional military bearing
Example: "Cessna one two three four five, Edwards Approach, squawk four five two one, turn right heading two seven zero, descend and maintain four thousand five hundred."
""",
        speech_rate=1.05,
        pitch_adjust=0.1,
        uses_abbreviations=False,
        verbose_explanations=False,
        radio_brevity="normal",
    ),
    
    ControllerRegion.INTERNATIONAL: ControllerPersonality(
        region=ControllerRegion.INTERNATIONAL,
        name="International",
        description="Clear and deliberate for non-native speakers. ICAO standard.",
        prompt_prefix="""You are an international controller using ICAO standard phraseology. Your communication style:
- Clear and deliberate speech
- Standard ICAO phraseology
- Avoid idioms or regional expressions
- Speak at moderate pace for clarity
- Use "affirm" instead of "yes", "negative" instead of "no"
- Full callsigns always
Example: "Cessna November one two three four five, Frankfurt Approach, radar contact, descend altitude three thousand feet, QNH one zero one three."
""",
        speech_rate=0.85,
        pitch_adjust=0.0,
        uses_abbreviations=False,
        verbose_explanations=True,
        radio_brevity="verbose",
    ),
}


def get_personality(region: ControllerRegion) -> ControllerPersonality:
    """Get personality configuration for a region."""
    return PERSONALITIES.get(region, PERSONALITIES[ControllerRegion.MIDWEST])


def get_personality_by_name(name: str) -> Optional[ControllerPersonality]:
    """Get personality by region name string."""
    for region, personality in PERSONALITIES.items():
        if region.value == name.lower() or personality.name.lower() == name.lower():
            return personality
    return None


def detect_region_from_position(lat: float, lon: float) -> ControllerRegion:
    """
    Attempt to detect region from aircraft position.
    
    This is a simple heuristic - could be extended with actual airspace data.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        Best-guess ControllerRegion
    """
    # Very rough US region detection
    # In reality, this should use actual facility/airspace data
    
    # New York Metro area (roughly)
    if 40.0 <= lat <= 42.0 and -75.0 <= lon <= -72.0:
        return ControllerRegion.NY_METRO
    
    # SoCal (roughly LA area)
    if 33.0 <= lat <= 35.0 and -119.0 <= lon <= -117.0:
        return ControllerRegion.SOCAL
    
    # Rural - very low population areas (Alaska, rural West, etc.)
    if lat > 60.0 or (lon < -110.0 and lat > 40.0):
        return ControllerRegion.RURAL
    
    # International - outside US
    if lon > -50.0 or lon < -130.0 or lat < 24.0 or lat > 50.0:
        return ControllerRegion.INTERNATIONAL
    
    # Default to Midwest/Standard
    return ControllerRegion.MIDWEST


def inject_personality_prompt(
    base_prompt: str,
    personality: ControllerPersonality,
) -> str:
    """
    Inject personality modifiers into the base ATC prompt.
    
    Args:
        base_prompt: The original ATC system prompt
        personality: Personality configuration to apply
        
    Returns:
        Modified prompt with personality context
    """
    # Find where to inject personality (after the initial role definition)
    # We'll prepend the personality prefix
    personality_block = f"""
=== CONTROLLER PERSONALITY: {personality.name.upper()} ===
{personality.prompt_prefix}
===
"""
    
    return personality_block + base_prompt


def get_tts_params(personality: ControllerPersonality) -> Dict[str, float]:
    """
    Get TTS parameter adjustments for a personality.
    
    Returns:
        Dict with 'rate' and 'pitch' adjustments
    """
    return {
        "rate": personality.speech_rate,
        "pitch": personality.pitch_adjust,
    }


def list_personalities() -> list:
    """List all available personalities."""
    return [
        {
            "id": p.region.value,
            "name": p.name,
            "description": p.description,
        }
        for p in PERSONALITIES.values()
    ]


# Test
if __name__ == "__main__":
    print("Available Controller Personalities:")
    print("=" * 60)
    
    for personality in PERSONALITIES.values():
        print(f"\n{personality.name} ({personality.region.value})")
        print(f"  {personality.description}")
        print(f"  Speech rate: {personality.speech_rate}x")
        print(f"  Brevity: {personality.radio_brevity}")
    
    print("\n" + "=" * 60)
    print("\nRegion Detection Test:")
    test_positions = [
        (40.7, -74.0, "New York"),
        (33.9, -118.4, "Los Angeles"),
        (41.8, -87.6, "Chicago"),
        (64.8, -147.7, "Fairbanks"),
        (51.5, -0.1, "London"),
    ]
    
    for lat, lon, name in test_positions:
        region = detect_region_from_position(lat, lon)
        print(f"  {name}: {region.value}")
