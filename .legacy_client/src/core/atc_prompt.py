"""
ATC Prompt Builder

STRATUS-009: Extracted from main_window.py for maintainability.

Builds context-aware prompts for the LLM to generate ATC responses.
"""

from typing import Optional, Dict, Any


def build_atc_prompt(
    telemetry,
    airports,
    flight_phase: str,
    history_context: str,
    message: str,
    overrides: Optional[Dict[str, str]] = None
) -> str:
    """
    Build the ATC system prompt with dynamic location context.
    
    Args:
        telemetry: SimTelemetry object with aircraft state
        airports: AirportManager for facility lookup
        flight_phase: Current flight phase string
        history_context: Recent conversation history
        message: Pilot's transmission text
        overrides: Dict with 'callsign' and 'type' overrides
        
    Returns:
        Complete prompt string for LLM
    """
    if overrides is None:
        overrides = {}
        
    # Determine Callsign: Manual Override > Telemetry Connected > Fallback
    manual_callsign = overrides.get("callsign", "")
    if manual_callsign:
        callsign = manual_callsign
    else:
        callsign = telemetry.tail_number if telemetry.connected else "November-One-Two-Three-Alpha-Bravo"

    # Determine Type (used in location context)
    manual_type = overrides.get("type", "")
    icao_type = manual_type if manual_type else telemetry.icao_type

    frequency = telemetry.com1.active
    
    # Default facility name
    facility_name = "Generic"

    # Build location context
    if telemetry.connected:
        location_context = _build_connected_context(
            telemetry, airports, flight_phase, 
            callsign, icao_type, frequency
        )
        facility_name = _get_facility_name(telemetry, airports)
    else:
        location_context = _build_disconnected_context(callsign)
        facility_name = "Local"

    # Build location-aware ATC prompt with FAA-accurate phraseology
    atc_prompt = _build_full_prompt(
        location_context, facility_name, callsign, 
        icao_type, history_context, message
    )
    
    return atc_prompt


def _build_connected_context(telemetry, airports, flight_phase, callsign, icao_type, frequency) -> str:
    """Build context when simulator is connected."""
    lat = telemetry.latitude
    lon = telemetry.longitude
    alt = int(telemetry.altitude_msl)
    on_ground = telemetry.on_ground
    heading = int(telemetry.heading_mag)
    speed = int(telemetry.ias)
    
    # Determine likely ATC facility type based on flight phase
    if on_ground:
        facility_hint = "Ground Control or Tower"
    elif alt < 3000:
        facility_hint = "Tower or Approach Control"
    elif alt < 18000:
        facility_hint = "Approach/Departure Control or Center"
    else:
        facility_hint = "Air Route Traffic Control Center (Center)"
    
    # Look up nearest airport
    nearest_apt = airports.find_nearest(lat, lon)
    if nearest_apt:
        raw_name = nearest_apt.name.replace(" Airport", "").replace(" Intl", "").replace(" International", "")
        facility_name = raw_name
    else:
        facility_name = "Local"
    
    return f"""
AIRCRAFT SITUATION:
- Aircraft: {callsign} (Type: {icao_type})
- Flight Phase: {flight_phase}
- Position: {lat:.4f}°N, {abs(lon):.4f}°{'W' if lon < 0 else 'E'}
- Nearest Facility: {facility_name} ({nearest_apt.icao if nearest_apt else 'Unknown'})
- Altitude: {alt} feet MSL
- Heading: {heading}°
- Speed: {speed} knots
- On Ground: {'Yes' if on_ground else 'No'}
- Radio Frequency: {frequency} MHz

You are Air Traffic Control at {facility_name}.
Facility type: {facility_hint}
"""


def _build_disconnected_context(callsign: str) -> str:
    """Build context when simulator is disconnected."""
    return f"""
AIRCRAFT SITUATION: Simulator disconnected - no position data available.
Aircraft: {callsign}
You are a generic Air Traffic Controller.
"""


def _get_facility_name(telemetry, airports) -> str:
    """Get the facility name based on position."""
    if not telemetry.connected:
        return "Local"
    
    nearest_apt = airports.find_nearest(telemetry.latitude, telemetry.longitude)
    if nearest_apt:
        return nearest_apt.name.replace(" Airport", "").replace(" Intl", "").replace(" International", "")
    return "Local"


def _build_full_prompt(location_context, facility_name, callsign, icao_type, history_context, message) -> str:
    """Build the complete ATC prompt with FAA phraseology examples."""
    return f"""{location_context}

=== CAPABILITY SCOPE ===
You are a VFR-ONLY ATC controller. You can handle:
✓ VFR flight following
✓ Traffic advisories  
✓ Pattern operations (Class D)
✓ Taxi and ground operations
✓ Basic weather/altimeter info

You CANNOT provide IFR services. If pilot requests:
- IFR clearances → "Unable, VFR services only"
- Instrument approaches → "Unable, VFR services only, check charts for approach frequency"
- SID/STAR routes → "Unable, VFR services only"
- IFR pickup → "Unable, contact Flight Service for IFR services"
========================

FAA ATC TRANSMISSION FORMAT:
Format: "[Aircraft Callsign], [Facility], [Message]"

OFFICIAL FAA VFR PHRASEOLOGY EXAMPLES (using YOUR callsign {callsign}):

1. INITIAL CONTACT (Cold Call):
Pilot: "{facility_name}, {callsign}, VFR request."
ATC: "{callsign}, {facility_name}, go ahead."

2. FLIGHT FOLLOWING REQUEST:
Pilot: "{callsign} is type {icao_type}, 5 miles south of {facility_name}, 4500, request flight following to Sacramento."
ATC: "{callsign}, squawk 4521, ident."
(NOTE: Assign a unique 4-digit squawk code. Do NOT give altimeter yet.)

3. RADAR CONTACT:
ATC: "{callsign}, radar contact, 5 miles south of {facility_name}. Altimeter 29.92."

4. SERVICE TERMINATION (Cancel Flight Following):
Pilot: "{callsign}, field in sight, cancel flight following."
ATC: "{callsign}, radar service terminated, squawk VFR, frequency change approved."

5. TRAFFIC ADVISORY:
ATC: "{callsign}, traffic 12 o'clock, 3 miles, northbound, altitude indicates 3500."

6. RADIO CHECK (Only if asked):
Pilot: "Radio check."
ATC: "{callsign}, readability five."

CRITICAL RULES:
1. ALWAYS use the EXACT callsign "{callsign}" - never substitute a different callsign
2. Start with aircraft callsign, then facility suffix (Ground, Tower, Approach, Center)
3. NEVER say "This is" - just the facility suffix directly  
4. Taxi clearances ALWAYS end with "hold short of runway [XX]"
5. Numbers: "niner" for 9, "two seven zero" for 270, "point" for decimal
6. Be extremely brief - real ATC is terse
7. Track the flight: if pilot requests flight following, acknowledge with squawk code and destination
8. If unsure about IFR procedures, say "Unable, VFR services only"


CONVERSATION CONTEXT:
{history_context}

The pilot now transmitted: "{message}"

Respond as ATC. Give ONLY the radio transmission, no explanations."""

