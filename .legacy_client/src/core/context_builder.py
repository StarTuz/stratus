"""
Context Window Maximization for Stratus ATC

Leverages the full local context window without cloud API cost concerns.
Injects rich context: airport diagrams, weather, NOTAMs, conversation history.

Cloud APIs charge per token. We don't.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ContextPriority(Enum):
    """Priority levels for context sections."""
    CRITICAL = 1    # Always include (system prompt, current request)
    HIGH = 2        # Include if space (conversation history)
    MEDIUM = 3      # Include if space (weather, airport)
    LOW = 4         # Include if space (NOTAMs, extended history)
    OPTIONAL = 5    # Nice to have (tips, examples)


@dataclass
class ContextSection:
    """A section of context to include in the prompt."""
    name: str
    content: str
    priority: ContextPriority
    token_estimate: int = 0  # Rough token count
    
    def __post_init__(self):
        # Estimate tokens (~4 chars per token)
        if self.token_estimate == 0:
            self.token_estimate = len(self.content) // 4


@dataclass
class ContextBudget:
    """Token budget for different model sizes."""
    model_name: str
    max_tokens: int
    reserved_for_response: int = 500  # Tokens reserved for output
    
    @property
    def available_tokens(self) -> int:
        return self.max_tokens - self.reserved_for_response


# Pre-defined budgets for common models
CONTEXT_BUDGETS: Dict[str, ContextBudget] = {
    "llama3.2:3b": ContextBudget("llama3.2:3b", max_tokens=8192),
    "llama3.1:8b": ContextBudget("llama3.1:8b", max_tokens=8192),
    "llama3:70b": ContextBudget("llama3:70b", max_tokens=8192),
    "mistral:7b": ContextBudget("mistral:7b", max_tokens=8192),
    "mixtral:8x7b": ContextBudget("mixtral:8x7b", max_tokens=32768),
    "qwen2.5:7b": ContextBudget("qwen2.5:7b", max_tokens=32768),
    "phi-3:mini": ContextBudget("phi-3:mini", max_tokens=4096),
    # Default for unknown models
    "default": ContextBudget("default", max_tokens=4096),
}


class ContextWindowBuilder:
    """
    Builds maximized context for ATC prompts.
    
    Intelligently packs as much relevant context as possible
    while respecting token limits.
    """
    
    def __init__(self, model_name: str = "llama3.2:3b"):
        """
        Initialize builder with model's context budget.
        
        Args:
            model_name: Ollama model name
        """
        self.model_name = model_name
        self.budget = CONTEXT_BUDGETS.get(model_name, CONTEXT_BUDGETS["default"])
        self._sections: List[ContextSection] = []
        
        logger.info(f"ContextWindowBuilder: {model_name}, budget={self.budget.max_tokens} tokens")
    
    def add_section(
        self,
        name: str,
        content: str,
        priority: ContextPriority,
    ):
        """Add a context section."""
        section = ContextSection(name=name, content=content, priority=priority)
        self._sections.append(section)
    
    def clear(self):
        """Clear all sections."""
        self._sections.clear()
    
    def add_system_prompt(self, prompt: str):
        """Add the core system prompt (always included)."""
        self.add_section("system_prompt", prompt, ContextPriority.CRITICAL)
    
    def add_user_request(self, request: str):
        """Add the current user request (always included)."""
        self.add_section("user_request", f"Pilot: {request}", ContextPriority.CRITICAL)
    
    def add_conversation_history(self, history: List[Dict[str, str]], max_turns: int = 10):
        """
        Add recent conversation history.
        
        Args:
            history: List of {"role": "pilot"|"atc", "message": "..."} entries
            max_turns: Maximum conversation turns to include
        """
        if not history:
            return
        
        recent = history[-max_turns:]
        formatted = "\n".join([
            f"{'Pilot' if h['role'] == 'pilot' else 'ATC'}: {h['message']}"
            for h in recent
        ])
        
        self.add_section(
            "conversation",
            f"[RECENT COMMUNICATIONS]\n{formatted}",
            ContextPriority.HIGH,
        )
    
    def add_airport_context(
        self,
        icao: str,
        runways: List[str],
        taxiways: List[str],
        frequencies: Dict[str, str],
    ):
        """Add airport diagram context."""
        content = f"""[AIRPORT: {icao}]
Runways: {', '.join(runways)}
Taxiways: {', '.join(taxiways)}
Frequencies:
"""
        for name, freq in frequencies.items():
            content += f"  {name}: {freq}\n"
        
        self.add_section("airport", content, ContextPriority.MEDIUM)
    
    def add_weather(
        self,
        metar: Optional[str] = None,
        wind: Optional[str] = None,
        altimeter: Optional[str] = None,
        ceiling: Optional[str] = None,
    ):
        """Add weather context."""
        parts = []
        if metar:
            parts.append(f"METAR: {metar}")
        if wind:
            parts.append(f"Wind: {wind}")
        if altimeter:
            parts.append(f"Altimeter: {altimeter}")
        if ceiling:
            parts.append(f"Ceiling: {ceiling}")
        
        if parts:
            content = "[WEATHER]\n" + "\n".join(parts)
            self.add_section("weather", content, ContextPriority.MEDIUM)
    
    def add_notams(self, notams: List[str], max_notams: int = 5):
        """Add relevant NOTAMs."""
        if not notams:
            return
        
        content = "[NOTAMS]\n"
        for notam in notams[:max_notams]:
            content += f"- {notam}\n"
        
        self.add_section("notams", content, ContextPriority.LOW)
    
    def add_traffic(self, traffic_reports: List[str]):
        """Add traffic in the pattern/area."""
        if not traffic_reports:
            return
        
        content = "[TRAFFIC IN AREA]\n"
        for report in traffic_reports:
            content += f"- {report}\n"
        
        self.add_section("traffic", content, ContextPriority.MEDIUM)
    
    def add_flight_plan(
        self,
        departure: str,
        destination: str,
        route: Optional[str] = None,
        altitude: Optional[int] = None,
    ):
        """Add filed flight plan context."""
        content = f"""[FLIGHT PLAN]
Departure: {departure}
Destination: {destination}"""
        if route:
            content += f"\nRoute: {route}"
        if altitude:
            content += f"\nFiled Altitude: {altitude}"
        
        self.add_section("flight_plan", content, ContextPriority.HIGH)
    
    def build(self) -> str:
        """
        Build the final context string, respecting token budget.
        
        Returns:
            Assembled context string within token limits
        """
        # Sort by priority
        sorted_sections = sorted(self._sections, key=lambda s: s.priority.value)
        
        available = self.budget.available_tokens
        included = []
        used_tokens = 0
        
        for section in sorted_sections:
            if used_tokens + section.token_estimate <= available:
                included.append(section)
                used_tokens += section.token_estimate
            else:
                if section.priority == ContextPriority.CRITICAL:
                    # Always include critical sections
                    included.append(section)
                    used_tokens += section.token_estimate
                    logger.warning(f"Context budget exceeded by critical section: {section.name}")
                else:
                    logger.debug(f"Trimmed section (out of budget): {section.name}")
        
        # Assemble in logical order
        result = []
        for section in included:
            result.append(section.content)
        
        final = "\n\n".join(result)
        
        logger.info(f"Context built: {used_tokens}/{available} tokens, {len(included)} sections")
        return final
    
    def get_stats(self) -> Dict[str, Any]:
        """Get build statistics."""
        total = sum(s.token_estimate for s in self._sections)
        return {
            "model": self.model_name,
            "budget_tokens": self.budget.max_tokens,
            "total_section_tokens": total,
            "sections_count": len(self._sections),
            "would_fit": total <= self.budget.available_tokens,
        }


# Convenience function for quick context building
def build_atc_context(
    system_prompt: str,
    user_request: str,
    callsign: str,
    airport: str,
    model: str = "llama3.2:3b",
    conversation_history: Optional[List[Dict[str, str]]] = None,
    weather_metar: Optional[str] = None,
    traffic: Optional[List[str]] = None,
) -> str:
    """
    Build a rich ATC context with all available information.
    
    Returns:
        Assembled prompt string
    """
    builder = ContextWindowBuilder(model)
    
    builder.add_system_prompt(system_prompt)
    builder.add_user_request(user_request)
    
    if conversation_history:
        builder.add_conversation_history(conversation_history)
    
    if weather_metar:
        builder.add_weather(metar=weather_metar)
    
    if traffic:
        builder.add_traffic(traffic)
    
    return builder.build()


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("Context Window Maximization Test")
    print("=" * 60)
    
    builder = ContextWindowBuilder("llama3.2:3b")
    
    # Add all sections
    builder.add_system_prompt("You are a professional ATC controller at Sacramento International...")
    builder.add_user_request("Request taxi to runway 28")
    
    builder.add_conversation_history([
        {"role": "pilot", "message": "Ground, Cessna 12345, at the FBO, request taxi"},
        {"role": "atc", "message": "Cessna 12345, Sacramento Ground, taxi to runway 28 via Alpha"},
    ])
    
    builder.add_airport_context(
        icao="KSMF",
        runways=["28L", "28R", "16L", "16R"],
        taxiways=["Alpha", "Bravo", "Charlie", "Delta"],
        frequencies={
            "Ground": "121.900",
            "Tower": "125.100",
            "ATIS": "127.600",
            "Approach": "124.500",
        },
    )
    
    builder.add_weather(
        metar="KSMF 120156Z 27008KT 10SM FEW080 21/10 A3001",
        wind="270 at 8",
        altimeter="30.01",
    )
    
    builder.add_notams([
        "RWY 16R closed for maintenance",
        "PAPI RWY 28L out of service",
    ])
    
    builder.add_traffic([
        "Citation on downwind 28L",
        "Mooney holding short 28R",
    ])
    
    # Build and display
    context = builder.build()
    print("\nBuilt Context:")
    print("-" * 60)
    print(context)
    print("-" * 60)
    print(f"\nStats: {builder.get_stats()}")
