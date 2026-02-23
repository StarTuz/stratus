"""
Ambient Radio Chatter for Stratus ATC

Generates occasional background radio transmissions for realism.
Makes the frequency feel lived-in with other aircraft.
"""

import logging
import threading
import time
import random
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ChatterType(Enum):
    """Types of ambient transmissions."""
    OTHER_AIRCRAFT = "other_aircraft"  # Other aircraft on frequency
    CONTROLLER = "controller"          # Controller to other aircraft
    BLOCKED = "blocked"                # Partially blocked transmission
    STATIC = "static"                  # Radio static


@dataclass
class AmbientTransmission:
    """A single ambient transmission."""
    text: str
    chatter_type: ChatterType
    delay_before: float = 0.0  # Seconds to wait before playing
    volume_adjust: float = 0.8  # Volume relative to main ATC


# Library of ambient transmissions
# These simulate other aircraft on the frequency

AMBIENT_LIBRARY: List[AmbientTransmission] = [
    # Other aircraft checking in
    AmbientTransmission(
        text="Regional 456, with you at flight level three five zero.",
        chatter_type=ChatterType.OTHER_AIRCRAFT,
    ),
    AmbientTransmission(
        text="Cherokee 789, ground point niner, taxi to parking.",
        chatter_type=ChatterType.OTHER_AIRCRAFT,
    ),
    AmbientTransmission(
        text="Skyhawk 234, thirty miles northwest, inbound full stop.",
        chatter_type=ChatterType.OTHER_AIRCRAFT,
    ),
    AmbientTransmission(
        text="United 892, requesting direct destination when able.",
        chatter_type=ChatterType.OTHER_AIRCRAFT,
    ),
    AmbientTransmission(
        text="Warrior 567, base to final runway two eight.",
        chatter_type=ChatterType.OTHER_AIRCRAFT,
    ),
    AmbientTransmission(
        text="November 345, clear of the runway.",
        chatter_type=ChatterType.OTHER_AIRCRAFT,
    ),
    AmbientTransmission(
        text="Bonanza 8 whiskey charlie, request left closed traffic.",
        chatter_type=ChatterType.OTHER_AIRCRAFT,
    ),
    
    # Controller to other traffic
    AmbientTransmission(
        text="American 738, contact departure, good day.",
        chatter_type=ChatterType.CONTROLLER,
    ),
    AmbientTransmission(
        text="Citation 5 romeo papa, cleared to land runway one six.",
        chatter_type=ChatterType.CONTROLLER,
    ),
    AmbientTransmission(
        text="Southwest 432, turn left heading zero niner zero.",
        chatter_type=ChatterType.CONTROLLER,
    ),
    AmbientTransmission(
        text="Delta 156, radar contact, climb maintain one seven thousand.",
        chatter_type=ChatterType.CONTROLLER,
    ),
    AmbientTransmission(
        text="Mooney 9 alpha bravo, extend downwind, traffic on base.",
        chatter_type=ChatterType.CONTROLLER,
    ),
    AmbientTransmission(
        text="November 234, expect left traffic runway two eight.",
        chatter_type=ChatterType.CONTROLLER,
    ),
    
    # Blocked/partial transmissions
    AmbientTransmission(
        text="...two thousand five...",
        chatter_type=ChatterType.BLOCKED,
        volume_adjust=0.5,
    ),
    AmbientTransmission(
        text="...heading three...",
        chatter_type=ChatterType.BLOCKED,
        volume_adjust=0.5,
    ),
    AmbientTransmission(
        text="...roger, wilco...",
        chatter_type=ChatterType.BLOCKED,
        volume_adjust=0.6,
    ),
]

# Uncontrolled field CTAF chatter
CTAF_LIBRARY: List[AmbientTransmission] = [
    AmbientTransmission(
        text="Lincoln traffic, Cessna 234, entering downwind runway one four, Lincoln.",
        chatter_type=ChatterType.OTHER_AIRCRAFT,
    ),
    AmbientTransmission(
        text="Lincoln traffic, Piper 567, short final one four, full stop, Lincoln.",
        chatter_type=ChatterType.OTHER_AIRCRAFT,
    ),
    AmbientTransmission(
        text="Lincoln traffic, Skyhawk departing runway one four, northbound, Lincoln.",
        chatter_type=ChatterType.OTHER_AIRCRAFT,
    ),
]


class AmbientChatterService:
    """
    Service that plays ambient radio chatter for realism.
    
    Randomly plays other aircraft and controller transmissions
    during quiet periods on the frequency.
    """
    
    def __init__(
        self,
        speak_func: Callable[[str, float], bool],  # (text, volume) -> success
        min_interval: float = 15.0,
        max_interval: float = 45.0,
        enabled: bool = True,
    ):
        """
        Initialize chatter service.
        
        Args:
            speak_func: Function to play audio (text, volume) -> success
            min_interval: Minimum seconds between transmissions
            max_interval: Maximum seconds between transmissions
            enabled: Whether chatter is enabled
        """
        self.speak_func = speak_func
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.enabled = enabled
        
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._library = AMBIENT_LIBRARY.copy()
        self._is_controlled = True  # Towered vs CTAF
        
        # Stats
        self.transmissions_played = 0
        
        logger.info("AmbientChatterService initialized")
    
    def start(self):
        """Start the chatter service."""
        if not self.enabled:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._chatter_loop, daemon=True)
        self._thread.start()
        logger.info("Ambient chatter service started")
    
    def stop(self):
        """Stop the chatter service."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Ambient chatter service stopped")
    
    def pause(self):
        """Pause chatter (e.g., when pilot is transmitting)."""
        self._paused = True
    
    def resume(self):
        """Resume chatter."""
        self._paused = False
    
    def set_controlled(self, is_controlled: bool):
        """Switch between controlled (towered) and uncontrolled (CTAF) mode."""
        self._is_controlled = is_controlled
        self._library = AMBIENT_LIBRARY if is_controlled else CTAF_LIBRARY
    
    def _chatter_loop(self):
        """Main loop for playing ambient chatter."""
        while self._running:
            # Wait for random interval
            interval = random.uniform(self.min_interval, self.max_interval)
            
            # Check frequently so we can stop quickly
            for _ in range(int(interval * 10)):
                if not self._running:
                    return
                time.sleep(0.1)
            
            # Skip if paused
            if self._paused:
                continue
            
            # Play a random transmission
            self._play_random_transmission()
    
    def _play_random_transmission(self):
        """Play a random ambient transmission."""
        if not self._library:
            return
        
        transmission = random.choice(self._library)
        
        try:
            logger.debug(f"Playing ambient: {transmission.text[:40]}...")
            success = self.speak_func(transmission.text, transmission.volume_adjust)
            if success:
                self.transmissions_played += 1
        except Exception as e:
            logger.error(f"Error playing ambient: {e}")
    
    def add_contextual_transmission(
        self,
        player_callsign: str,
        position_in_sequence: int,
        traffic_description: str,
    ):
        """
        Add a transmission that references the player's aircraft.
        
        This makes the player feel part of the traffic flow.
        
        Args:
            player_callsign: The player's callsign
            position_in_sequence: Player's position in traffic sequence
            traffic_description: Description of player for other ATC use
        """
        # Example: "Cessna 234, number 2 following a Skyhawk on 3-mile final"
        if position_in_sequence == 2:
            text = f"Number 2 traffic is a {traffic_description}, report them in sight."
            transmission = AmbientTransmission(
                text=text,
                chatter_type=ChatterType.CONTROLLER,
            )
            self._library.append(transmission)
    
    def get_stats(self) -> dict:
        """Get service statistics."""
        return {
            "enabled": self.enabled,
            "running": self._running,
            "paused": self._paused,
            "transmissions_played": self.transmissions_played,
            "library_size": len(self._library),
        }


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    def mock_speak(text: str, volume: float) -> bool:
        print(f"[CHATTER @ {volume:.1f}] {text}")
        return True
    
    service = AmbientChatterService(
        speak_func=mock_speak,
        min_interval=3.0,  # Fast for testing
        max_interval=5.0,
    )
    
    print("Starting ambient chatter test (20 seconds)...")
    service.start()
    
    try:
        time.sleep(20)
    except KeyboardInterrupt:
        pass
    
    service.stop()
    print(f"\nTotal transmissions: {service.transmissions_played}")
