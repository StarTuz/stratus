"""
ATC Handoff Manager

STRATUS-007: Implement facility transitions (Tower → Departure → Center → Approach → Tower).

Tracks:
- Current controlling facility
- Expected handoff triggers
- Handoff phraseology generation
"""

import logging
from enum import Enum, auto
from typing import Optional, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class FacilityType(Enum):
    """Types of ATC facilities."""
    UNKNOWN = auto()
    CLEARANCE = auto()      # Clearance Delivery
    GROUND = auto()         # Ground Control
    TOWER = auto()          # Tower (local control)
    DEPARTURE = auto()      # Departure Control (TRACON)
    APPROACH = auto()       # Approach Control (TRACON)
    CENTER = auto()         # Air Route Traffic Control Center (ARTCC)
    UNICOM = auto()         # Uncontrolled field
    FLIGHT_SERVICE = auto() # FSS
    
    def to_name(self, identifier: str = "") -> str:
        """Get readable facility name."""
        base_names = {
            FacilityType.CLEARANCE: "Clearance",
            FacilityType.GROUND: "Ground",
            FacilityType.TOWER: "Tower",
            FacilityType.DEPARTURE: "Departure",
            FacilityType.APPROACH: "Approach",
            FacilityType.CENTER: "Center",
            FacilityType.UNICOM: "Traffic",
            FacilityType.FLIGHT_SERVICE: "Radio",
        }
        name = base_names.get(self, "ATC")
        if identifier:
            return f"{identifier} {name}"
        return name


@dataclass
class Facility:
    """Represents an ATC facility."""
    type: FacilityType
    identifier: str         # e.g., "NorCal", "SoCal", "Oakland"
    frequency: str          # Primary frequency
    
    @property
    def name(self) -> str:
        return self.type.to_name(self.identifier)


@dataclass
class HandoffTrigger:
    """Conditions that trigger a handoff."""
    altitude_above: Optional[int] = None    # Handoff when above this altitude
    altitude_below: Optional[int] = None    # Handoff when below this altitude
    distance_from_airport: Optional[float] = None  # nm from departure/arrival
    phase_change: Optional[str] = None      # When entering this phase


class HandoffManager:
    """
    Manage ATC facility handoffs based on flight phase and position.
    """
    
    def __init__(self):
        self._current_facility: Optional[Facility] = None
        self._departure_airport: Optional[str] = None
        self._arrival_airport: Optional[str] = None
        self._last_handoff_altitude: float = 0
        self._handoff_history: List[Tuple[str, str]] = []  # (from, to)
    
    @property
    def current_facility(self) -> Optional[Facility]:
        return self._current_facility
    
    @property
    def current_facility_name(self) -> str:
        if self._current_facility:
            return self._current_facility.name
        return "Unknown"
    
    def set_departure_airport(self, icao: str):
        """Set the departure airport for handoff logic."""
        self._departure_airport = icao
        logger.info(f"[HANDOFF] Departure set: {icao}")
    
    def set_arrival_airport(self, icao: str):
        """Set the arrival airport for handoff logic."""
        self._arrival_airport = icao
        logger.info(f"[HANDOFF] Arrival set: {icao}")
    
    def update(self, telemetry, flight_phase: str) -> Optional[str]:
        """
        Check if a handoff should occur based on current state.
        
        Returns handoff phraseology if handoff triggered, None otherwise.
        """
        if not telemetry or not telemetry.connected:
            return None
        
        alt_msl = telemetry.altitude_msl
        on_ground = telemetry.on_ground
        
        # Determine expected facility based on phase and altitude
        expected_facility = self._determine_expected_facility(
            flight_phase, alt_msl, on_ground
        )
        
        # Check if we need to handoff
        if expected_facility and (
            self._current_facility is None or 
            expected_facility.type != self._current_facility.type
        ):
            phraseology = self._generate_handoff(expected_facility)
            self._current_facility = expected_facility
            self._last_handoff_altitude = alt_msl
            return phraseology
        
        return None
    
    def _determine_expected_facility(
        self, 
        phase: str, 
        altitude: float, 
        on_ground: bool
    ) -> Optional[Facility]:
        """Determine which facility should be controlling based on phase."""
        
        # Map phase strings to facility types
        # This is simplified - real logic would use airport data
        
        if on_ground:
            if "parked" in phase.lower() or "taxi" in phase.lower():
                return Facility(
                    type=FacilityType.GROUND,
                    identifier=self._departure_airport or "",
                    frequency="121.900"  # Common ground freq
                )
        
        if "takeoff" in phase.lower() or "departure" in phase.lower():
            if altitude < 3000:
                return Facility(
                    type=FacilityType.TOWER,
                    identifier=self._departure_airport or "",
                    frequency="118.300"
                )
            elif altitude < 10000:
                return Facility(
                    type=FacilityType.DEPARTURE,
                    identifier="",
                    frequency="124.000"
                )
        
        if "cruise" in phase.lower() or altitude > 18000:
            return Facility(
                type=FacilityType.CENTER,
                identifier="",
                frequency="127.750"
            )
        
        if "descent" in phase.lower() or "approach" in phase.lower():
            if altitude > 10000:
                return Facility(
                    type=FacilityType.CENTER,
                    identifier="",
                    frequency="127.750"
                )
            else:
                return Facility(
                    type=FacilityType.APPROACH,
                    identifier="",
                    frequency="124.350"
                )
        
        return None
    
    def _generate_handoff(self, to_facility: Facility) -> str:
        """Generate ATC handoff phraseology."""
        from_name = self._current_facility.name if self._current_facility else "frequency"
        
        # Track handoff history
        self._handoff_history.append((from_name, to_facility.name))
        
        logger.info(f"[HANDOFF] {from_name} → {to_facility.name} on {to_facility.frequency}")
        
        # Generate phraseology
        return f"Contact {to_facility.name} on {to_facility.frequency}"
    
    def force_handoff_to(self, facility_type: FacilityType, identifier: str, frequency: str):
        """Manually trigger a handoff (e.g., from pilot request)."""
        new_facility = Facility(
            type=facility_type,
            identifier=identifier,
            frequency=frequency
        )
        phraseology = self._generate_handoff(new_facility)
        self._current_facility = new_facility
        return phraseology
    
    def get_atc_context(self) -> str:
        """Get current facility for ATC prompt context."""
        if self._current_facility:
            return f"Currently with: {self._current_facility.name}"
        return "Facility: Unknown"
    
    def reset(self):
        """Reset for new flight."""
        self._current_facility = None
        self._departure_airport = None
        self._arrival_airport = None
        self._last_handoff_altitude = 0
        self._handoff_history.clear()
        logger.info("[HANDOFF] Manager reset")


# Global instance
_manager: Optional[HandoffManager] = None


def get_handoff_manager() -> HandoffManager:
    """Get the global handoff manager instance."""
    global _manager
    if _manager is None:
        _manager = HandoffManager()
    return _manager
