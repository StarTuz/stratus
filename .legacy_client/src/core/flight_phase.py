"""
Flight Phase Tracker

STRATUS-005: Track aircraft through flight phases for context-aware ATC.

Phases:
1. PARKED - Engine off or idle at gate
2. TAXI_OUT - Moving on ground toward runway
3. TAKEOFF - Takeoff roll and initial climb
4. DEPARTURE - Climbing out <10,000ft
5. CRUISE - Level flight enroute
6. DESCENT - Descending toward destination
7. APPROACH - Final approach phase
8. LANDING - Touchdown and rollout
9. TAXI_IN - Taxiing to gate after landing
"""

import logging
from enum import Enum, auto
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class FlightPhase(Enum):
    """Flight phases as they would be recognized by ATC."""
    UNKNOWN = auto()
    PARKED = auto()         # At gate, engines off/idle
    TAXI_OUT = auto()       # Moving on ground toward runway
    TAKEOFF = auto()        # Takeoff roll
    DEPARTURE = auto()      # Initial climb (<10,000ft typically)
    CRUISE = auto()         # Level flight at altitude
    DESCENT = auto()        # Descending
    APPROACH = auto()       # Final approach (pattern entry to touchdown)
    LANDING = auto()        # Rollout after touchdown
    TAXI_IN = auto()        # Taxiing to parking
    
    def to_atc_context(self) -> str:
        """Return phase description for ATC prompt context."""
        return {
            FlightPhase.UNKNOWN: "Unknown phase",
            FlightPhase.PARKED: "Parked at gate/ramp",
            FlightPhase.TAXI_OUT: "Taxiing for departure",
            FlightPhase.TAKEOFF: "Takeoff roll / initial climb",
            FlightPhase.DEPARTURE: "Departing, climbing",
            FlightPhase.CRUISE: "Cruising at altitude",
            FlightPhase.DESCENT: "Descending",
            FlightPhase.APPROACH: "On approach",
            FlightPhase.LANDING: "Landing / rollout",
            FlightPhase.TAXI_IN: "Taxiing to parking",
        }.get(self, "Unknown")


@dataclass
class PhaseThresholds:
    """Configurable thresholds for phase detection."""
    # Ground detection
    taxi_speed_max: float = 40.0        # kts - below this is taxi/parked
    takeoff_speed_min: float = 50.0     # kts - above this on ground = takeoff
    
    # Climb/Descent detection (fpm)
    climb_vs_threshold: float = 300.0   # fpm - above this = climbing
    descent_vs_threshold: float = -300.0  # fpm - below this = descending
    
    # Altitude thresholds
    pattern_altitude_agl: float = 2000.0  # ft AGL - below this = pattern/approach
    departure_altitude_msl: float = 10000.0  # ft MSL - below this = departure
    
    # Timing (seconds to confirm phase change)
    phase_confirm_time: float = 3.0


class FlightPhaseTracker:
    """
    Track flight phase using state machine logic.
    
    Uses hysteresis and timing to prevent rapid phase switching.
    """
    
    def __init__(self, thresholds: Optional[PhaseThresholds] = None):
        self._thresholds = thresholds or PhaseThresholds()
        self._current_phase = FlightPhase.UNKNOWN
        self._pending_phase: Optional[FlightPhase] = None
        self._phase_start_time: float = 0.0
        self._last_update_time: float = 0.0
        
        # Flight tracking
        self._max_altitude_reached: float = 0.0
        self._was_airborne: bool = False
        
    @property
    def current_phase(self) -> FlightPhase:
        return self._current_phase
    
    @property
    def phase_name(self) -> str:
        return self._current_phase.name
    
    def update(self, telemetry) -> FlightPhase:
        """
        Update phase based on current telemetry.
        
        Args:
            telemetry: SimTelemetry object with aircraft state
            
        Returns:
            Current flight phase
        """
        if not telemetry or not telemetry.connected:
            return FlightPhase.UNKNOWN
        
        import time
        current_time = time.time()
        
        # Detect the logical phase
        detected_phase = self._detect_phase(telemetry)
        
        # Track max altitude for descent detection
        if telemetry.altitude_msl > self._max_altitude_reached:
            self._max_altitude_reached = telemetry.altitude_msl
        
        # Track if we've been airborne
        if not telemetry.on_ground:
            self._was_airborne = True
        
        # Phase change logic with hysteresis
        if detected_phase != self._current_phase:
            if detected_phase == self._pending_phase:
                # Same pending phase, check if we should confirm
                elapsed = current_time - self._phase_start_time
                if elapsed >= self._thresholds.phase_confirm_time:
                    self._transition_to(detected_phase)
            else:
                # New pending phase
                self._pending_phase = detected_phase
                self._phase_start_time = current_time
        else:
            # Phase matches, clear pending
            self._pending_phase = None
        
        self._last_update_time = current_time
        return self._current_phase
    
    def _detect_phase(self, telemetry) -> FlightPhase:
        """Detect the logical phase based on telemetry values."""
        on_ground = telemetry.on_ground
        ias = telemetry.ias
        vs = telemetry.vertical_speed
        alt_msl = telemetry.altitude_msl
        alt_agl = getattr(telemetry, 'altitude_agl', alt_msl)  # Fallback if no AGL
        
        t = self._thresholds
        
        # ON GROUND PHASES
        if on_ground:
            if ias < 10:
                # Very slow or stopped
                if self._was_airborne:
                    return FlightPhase.TAXI_IN
                else:
                    return FlightPhase.PARKED
            elif ias < t.taxi_speed_max:
                # Moving slowly on ground
                if self._was_airborne:
                    return FlightPhase.TAXI_IN
                else:
                    return FlightPhase.TAXI_OUT
            else:
                # Fast on ground
                if self._was_airborne:
                    return FlightPhase.LANDING
                else:
                    return FlightPhase.TAKEOFF
        
        # AIRBORNE PHASES
        else:
            # Check vertical speed
            if vs > t.climb_vs_threshold:
                # Climbing
                if alt_msl < t.departure_altitude_msl:
                    return FlightPhase.DEPARTURE
                else:
                    # Could be cruise-climb or step climb
                    return FlightPhase.CRUISE
                    
            elif vs < t.descent_vs_threshold:
                # Descending
                if alt_agl < t.pattern_altitude_agl:
                    return FlightPhase.APPROACH
                else:
                    return FlightPhase.DESCENT
            else:
                # Level flight
                if alt_agl < t.pattern_altitude_agl:
                    # Low and level - probably in pattern
                    return FlightPhase.APPROACH
                else:
                    return FlightPhase.CRUISE
    
    def _transition_to(self, new_phase: FlightPhase):
        """Perform phase transition with logging."""
        old_phase = self._current_phase
        self._current_phase = new_phase
        self._pending_phase = None
        
        logger.info(f"[PHASE] Transition: {old_phase.name} → {new_phase.name}")
        
        # Reset tracking on new flight
        if new_phase == FlightPhase.PARKED:
            self._max_altitude_reached = 0.0
            self._was_airborne = False
    
    def reset(self):
        """Reset tracker for new flight."""
        self._current_phase = FlightPhase.UNKNOWN
        self._pending_phase = None
        self._max_altitude_reached = 0.0
        self._was_airborne = False
        logger.info("[PHASE] Tracker reset")
    
    def get_atc_context(self) -> str:
        """Get phase description for ATC prompt context."""
        return self._current_phase.to_atc_context()
    
    def get_expected_services(self) -> list:
        """
        Return the ATC services typically expected in this phase.
        
        Used to guide prompt construction.
        """
        phase_services = {
            FlightPhase.PARKED: ["Clearance Delivery", "Ground"],
            FlightPhase.TAXI_OUT: ["Ground"],
            FlightPhase.TAKEOFF: ["Tower"],
            FlightPhase.DEPARTURE: ["Tower", "Departure"],
            FlightPhase.CRUISE: ["Center", "Flight Following"],
            FlightPhase.DESCENT: ["Center", "Approach"],
            FlightPhase.APPROACH: ["Approach", "Tower"],
            FlightPhase.LANDING: ["Tower"],
            FlightPhase.TAXI_IN: ["Ground"],
        }
        return phase_services.get(self._current_phase, ["Unknown"])


# Global tracker instance
_tracker: Optional[FlightPhaseTracker] = None


def get_flight_phase_tracker() -> FlightPhaseTracker:
    """Get the global flight phase tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = FlightPhaseTracker()
    return _tracker
