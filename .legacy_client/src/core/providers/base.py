from abc import ABC, abstractmethod
from typing import Optional, List, Any, Dict
from dataclasses import dataclass, field
from enum import Enum
import time

# --- Shared Data Types (Moved from sapi_interface.py) ---

class Channel(Enum):
    COM1 = "COM1"
    COM2 = "COM2"
    INTERCOM = "INTERCOM"
    # Surround channels for Local Provider
    LEFT_EAR = "left"
    RIGHT_EAR = "right"

class Entity(Enum):
    ATC = "atc"
    COPILOT = "copilot"
    CREW = "crew"
    DISPATCHER = "dispatcher"
    TOUR_GUIDE = "tourguide"
    MENTOR = "mentor"

@dataclass
class CommEntry:
    station_name: str = ""
    ident: str = ""
    frequency: str = ""
    incoming_message: str = ""
    outgoing_message: str = ""
    atc_url: Optional[str] = None
    pilot_url: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class ATCResponse:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None

# --- Abstract Base Class ---

class IATCProvider(ABC):
    """
    Abstract interface for ATC/Speech providers.
    Currently uses Local provider (SpeechD-NG + Ollama).
    """

    @abstractmethod
    def connect(self) -> bool:
        """Initialize connection to the backend."""
        pass

    @abstractmethod
    def disconnect(self):
        """Clean up connection."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if connected to provider."""
        pass

    @abstractmethod
    def get_status(self) -> str:
        """Return connection status."""
        pass

    @abstractmethod
    def say(self, text: str, voice: Optional[str] = None, channel: Optional[str] = None) -> ATCResponse:
        """
        Speak text via TTS.
        channel: 'left', 'right', 'stereo', or None (default)
        """
        pass

    @abstractmethod
    def think(self, context: str) -> ATCResponse:
        """
        Send text/context to the 'Brain' and get a text response.
        Used for determine ATC instructions.
        """
        pass

    @abstractmethod
    def listen(self, timeout_sec: int = 5) -> ATCResponse:
        """
        Listen for pilot voice input and return text (STT).
        """
        pass
        
    def get_comms_history(self, lat: float = None, lon: float = None) -> ATCResponse:
        """Return communications history."""
        # Default empty implementation if not overridden
        return ATCResponse(True, data=[])

    def set_variable(self, name: str, value: str, unit: str = "") -> bool:
        """Set a context variable for the AI."""
        return True

    def set_frequency(self, frequency: str, channel: str = "COM1") -> ATCResponse:
        """Set active frequency for a channel."""
        return ATCResponse(True)

    def say_as(self, text: str, entity: str = "pilot", channel: str = "COM1") -> ATCResponse:
        """Legacy compatibility for sending transmissions."""
        return self.say(text)

    # --- Legacy/Shared Methods (Optional implementation) ---
    
    def update_telemetry(self, t: Dict[str, Any]) -> ATCResponse:
        """Send aircraft telemetry (if backend requires it)."""
        return ATCResponse(True)
