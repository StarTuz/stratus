"""
Speculative Pre-generation Cache for Stratus ATC

Pre-generates likely ATC responses based on current flight phase.
When pilot speaks, fuzzy-match to cache for instant response.

Sub-200ms response for common exchanges.
"""

import logging
import threading
import time
import hashlib
from typing import Optional, Dict, List, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FlightPhase(Enum):
    """Current phase of flight."""
    PARKED = "parked"
    TAXI_OUT = "taxi_out"
    HOLDING = "holding"
    TAKEOFF = "takeoff"
    DEPARTURE = "departure"
    CRUISE = "cruise"
    DESCENT = "descent"
    APPROACH = "approach"
    LANDING = "landing"
    TAXI_IN = "taxi_in"


@dataclass
class CachedResponse:
    """A pre-generated response in cache."""
    intent_key: str              # Unique key for this intent
    prompt_template: str         # Template used for generation
    response_text: str           # Pre-generated response
    flight_phase: FlightPhase    # Phase this applies to
    context_hash: str            # Hash of context when generated
    generated_at: float          # Timestamp
    hit_count: int = 0           # Usage counter


@dataclass
class CacheStats:
    """Statistics for cache performance."""
    hits: int = 0
    misses: int = 0
    generations: int = 0
    invalidations: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


# Common pilot intents by flight phase
PHASE_INTENTS: Dict[FlightPhase, List[Tuple[str, str]]] = {
    
    FlightPhase.PARKED: [
        ("request_taxi", "Pilot requests taxi clearance"),
        ("request_ifr_clearance", "Pilot requests IFR clearance"),
        ("atis_check", "Pilot has ATIS information"),
    ],
    
    FlightPhase.TAXI_OUT: [
        ("hold_short_readback", "Pilot reads back hold short"),
        ("ready_for_departure", "Pilot reports ready for departure"),
        ("request_intersection", "Pilot requests intersection departure"),
    ],
    
    FlightPhase.HOLDING: [
        ("ready_for_takeoff", "Pilot reports ready for takeoff"),
        ("line_up_and_wait", "Pilot acknowledges line up and wait"),
    ],
    
    FlightPhase.TAKEOFF: [
        ("contact_departure", "Pilot contacts departure"),
        ("airborne_check_in", "Pilot checks in after takeoff"),
    ],
    
    FlightPhase.DEPARTURE: [
        ("altitude_leaving", "Pilot reports leaving altitude"),
        ("request_flight_following", "Pilot requests VFR flight following"),
    ],
    
    FlightPhase.CRUISE: [
        ("position_report", "Pilot gives position report"),
        ("request_altitude_change", "Pilot requests altitude change"),
        ("weather_request", "Pilot requests weather update"),
        ("radio_check", "Pilot requests radio check"),
    ],
    
    FlightPhase.DESCENT: [
        ("request_lower", "Pilot requests lower altitude"),
        ("atis_received", "Pilot reports ATIS received"),
    ],
    
    FlightPhase.APPROACH: [
        ("airport_in_sight", "Pilot reports airport in sight"),
        ("request_straight_in", "Pilot requests straight-in approach"),
        ("request_pattern", "Pilot requests pattern entry"),
    ],
    
    FlightPhase.LANDING: [
        ("clear_of_runway", "Pilot reports clear of runway"),
        ("request_taxi_parking", "Pilot requests taxi to parking"),
    ],
    
    FlightPhase.TAXI_IN: [
        ("at_gate", "Pilot reports at gate/parking"),
    ],
}


class SpeculativeCache:
    """
    Cache for pre-generated ATC responses.
    
    Pre-generates likely responses based on flight phase and context.
    When pilot speaks, attempt to match to cache for instant response.
    """
    
    def __init__(
        self,
        generate_func: Callable[[str], str],
        max_cache_size: int = 20,
        ttl_seconds: float = 300.0,  # 5 minutes
    ):
        """
        Initialize cache.
        
        Args:
            generate_func: Function to generate LLM response (prompt -> response)
            max_cache_size: Maximum cached responses
            ttl_seconds: Time-to-live for cached responses
        """
        self.generate_func = generate_func
        self.max_cache_size = max_cache_size
        self.ttl_seconds = ttl_seconds
        
        self._cache: Dict[str, CachedResponse] = {}
        self._stats = CacheStats()
        self._lock = threading.Lock()
        self._current_context_hash: str = ""
        
        # Background generation thread
        self._generation_queue: List[Tuple[str, str, FlightPhase]] = []
        self._generation_thread: Optional[threading.Thread] = None
        self._running = False
        
        logger.info(f"SpeculativeCache initialized: max_size={max_cache_size}, ttl={ttl_seconds}s")
    
    def start(self):
        """Start background generation."""
        self._running = True
        self._generation_thread = threading.Thread(target=self._generation_loop, daemon=True)
        self._generation_thread.start()
    
    def stop(self):
        """Stop background generation."""
        self._running = False
        if self._generation_thread:
            self._generation_thread.join(timeout=2.0)
    
    def update_context(
        self,
        phase: FlightPhase,
        airport: str,
        runway: str,
        callsign: str,
        frequency: str,
    ):
        """
        Update current context and regenerate cache if changed.
        
        Args:
            phase: Current flight phase
            airport: Current/target airport
            runway: Active runway
            callsign: Aircraft callsign
            frequency: Current frequency
        """
        # Build context hash
        context_str = f"{phase.value}|{airport}|{runway}|{callsign}|{frequency}"
        new_hash = hashlib.md5(context_str.encode()).hexdigest()[:8]
        
        if new_hash != self._current_context_hash:
            logger.info(f"Context changed, invalidating cache: {new_hash}")
            self._invalidate_cache()
            self._current_context_hash = new_hash
            
            # Queue new generations for this phase
            self._queue_phase_generations(phase, airport, runway, callsign, frequency)
    
    def _queue_phase_generations(
        self,
        phase: FlightPhase,
        airport: str,
        runway: str,
        callsign: str,
        frequency: str,
    ):
        """Queue generation of likely responses for current phase."""
        intents = PHASE_INTENTS.get(phase, [])
        
        for intent_key, intent_description in intents:
            prompt = self._build_prompt(
                intent_description,
                airport=airport,
                runway=runway,
                callsign=callsign,
                frequency=frequency,
            )
            self._generation_queue.append((intent_key, prompt, phase))
        
        logger.debug(f"Queued {len(intents)} generations for phase {phase.value}")
    
    def _build_prompt(
        self,
        intent: str,
        airport: str,
        runway: str,
        callsign: str,
        frequency: str,
    ) -> str:
        """Build a prompt for pre-generation."""
        return f"""You are ATC at {airport}. Active runway is {runway}.
        
The pilot ({callsign}) on frequency {frequency} makes this request:
{intent}

Respond with proper ATC phraseology. Be brief and realistic."""
    
    def _generation_loop(self):
        """Background loop for generating responses."""
        while self._running:
            if self._generation_queue:
                try:
                    intent_key, prompt, phase = self._generation_queue.pop(0)
                    self._generate_and_cache(intent_key, prompt, phase)
                except Exception as e:
                    logger.error(f"Generation error: {e}")
            else:
                time.sleep(0.5)
    
    def _generate_and_cache(self, intent_key: str, prompt: str, phase: FlightPhase):
        """Generate and cache a response."""
        try:
            response = self.generate_func(prompt)
            if response:
                with self._lock:
                    self._cache[intent_key] = CachedResponse(
                        intent_key=intent_key,
                        prompt_template=prompt,
                        response_text=response,
                        flight_phase=phase,
                        context_hash=self._current_context_hash,
                        generated_at=time.time(),
                    )
                    self._stats.generations += 1
                    
                    # Trim cache if too large
                    self._trim_cache()
                    
                logger.debug(f"Cached response for intent: {intent_key}")
                
        except Exception as e:
            logger.error(f"Failed to generate for {intent_key}: {e}")
    
    def get(self, intent_key: str) -> Optional[str]:
        """
        Get cached response for an intent.
        
        Args:
            intent_key: The intent to look up
            
        Returns:
            Cached response text, or None if not found
        """
        with self._lock:
            entry = self._cache.get(intent_key)
            
            if entry is None:
                self._stats.misses += 1
                return None
            
            # Check TTL
            age = time.time() - entry.generated_at
            if age > self.ttl_seconds:
                del self._cache[intent_key]
                self._stats.misses += 1
                return None
            
            # Check context hash
            if entry.context_hash != self._current_context_hash:
                self._stats.misses += 1
                return None
            
            entry.hit_count += 1
            self._stats.hits += 1
            
            logger.info(f"Cache HIT for {intent_key} (latency: ~0ms)")
            return entry.response_text
    
    def fuzzy_match(self, pilot_message: str) -> Optional[Tuple[str, str]]:
        """
        Attempt to fuzzy match pilot message to cached intent.
        
        Args:
            pilot_message: What the pilot said
            
        Returns:
            (intent_key, response) tuple if matched, else None
        """
        message_lower = pilot_message.lower()
        
        # Simple keyword matching - could be enhanced with embeddings
        keywords_map = {
            "request_taxi": ["taxi", "clearance", "ground"],
            "ready_for_departure": ["ready", "departure", "takeoff"],
            "hold_short_readback": ["hold short", "holding short"],
            "request_flight_following": ["flight following", "vfr", "advisories"],
            "position_report": ["position", "over", "reporting"],
            "airport_in_sight": ["airport in sight", "field in sight"],
            "clear_of_runway": ["clear", "runway", "off the runway"],
            "radio_check": ["radio check", "how do you read"],
        }
        
        for intent_key, keywords in keywords_map.items():
            if any(kw in message_lower for kw in keywords):
                response = self.get(intent_key)
                if response:
                    return (intent_key, response)
        
        return None
    
    def _invalidate_cache(self):
        """Clear the cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.invalidations += 1
            logger.debug(f"Cache invalidated, cleared {count} entries")
    
    def _trim_cache(self):
        """Remove oldest entries if cache exceeds max size."""
        if len(self._cache) <= self.max_cache_size:
            return
        
        # Sort by generated_at and remove oldest
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].generated_at,
        )
        
        to_remove = len(self._cache) - self.max_cache_size
        for intent_key, _ in sorted_entries[:to_remove]:
            del self._cache[intent_key]
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats


# Convenience test
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Mock generate function
    def mock_generate(prompt: str) -> str:
        time.sleep(0.5)  # Simulate LLM latency
        return f"[MOCK ATC RESPONSE for: {prompt[:50]}...]"
    
    cache = SpeculativeCache(mock_generate)
    cache.start()
    
    # Simulate context update
    cache.update_context(
        phase=FlightPhase.TAXI_OUT,
        airport="KSMF",
        runway="28",
        callsign="N12345",
        frequency="121.900",
    )
    
    # Wait for background generation
    time.sleep(3)
    
    # Try to match
    result = cache.fuzzy_match("Ready for departure")
    print(f"Match result: {result}")
    
    print(f"Stats: hits={cache._stats.hits}, misses={cache._stats.misses}")
    
    cache.stop()
