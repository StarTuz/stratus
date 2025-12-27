"""
SayIntentions API (SAPI) Interface Module

This module provides a complete Python interface to the SayIntentions cloud API.
It handles all REST endpoint communication for the native Linux/Mac client.

Base URL: https://apipri.sayintentions.ai/sapi/
Authentication: API key as URL parameter (?api_key=XXX)
Documentation: https://p2.sayintentions.ai/p2/docs/
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import configparser
import requests
import logging
import time
import os


# =============================================================================
# Data Classes
# =============================================================================

class Channel(Enum):
    """Radio channels for communication"""
    COM1 = "COM1"
    COM2 = "COM2"
    INTERCOM = "INTERCOM"


class Entity(Enum):
    """Entity types that can speak"""
    ATC = "atc"
    COPILOT = "copilot"
    CREW = "crew"
    DISPATCHER = "dispatcher"


@dataclass
class CommEntry:
    """Represents a single communication entry from getCommsHistory"""
    station_name: str = ""
    ident: str = ""  # ICAO identifier
    frequency: str = ""
    incoming_message: str = ""  # Pilot's message
    outgoing_message: str = ""  # ATC's response
    atc_url: Optional[str] = None  # URL for ATC audio
    pilot_url: Optional[str] = None  # URL for pilot audio
    timestamp: float = field(default_factory=time.time)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommEntry":
        """Create CommEntry from API response dict"""
        return cls(
            station_name=data.get("station_name", ""),
            ident=data.get("ident", ""),
            frequency=data.get("frequency", ""),
            incoming_message=data.get("incoming_message", ""),
            outgoing_message=data.get("outgoing_message", ""),
            atc_url=data.get("atc_url"),
            pilot_url=data.get("pilot_url"),
            timestamp=data.get("timestamp", time.time())
        )


@dataclass
class WeatherData:
    """Weather data from getWX endpoint"""
    icao: str
    atis: str = ""
    metar: str = ""
    taf: str = ""
    
    @classmethod
    def from_dict(cls, icao: str, data: Dict[str, Any]) -> "WeatherData":
        return cls(
            icao=icao,
            atis=data.get("atis", ""),
            metar=data.get("metar", ""),
            taf=data.get("taf", "")
        )


@dataclass
class ParkingInfo:
    """Parking/gate information from getParking endpoint"""
    gate: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    heading: float = 0.0
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParkingInfo":
        return cls(
            gate=data.get("gate", ""),
            latitude=data.get("lat", 0.0),
            longitude=data.get("lon", 0.0),
            heading=data.get("hdg", 0.0)
        )


@dataclass
class SapiResponse:
    """Generic response wrapper for SAPI calls"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    status_code: int = 0


# =============================================================================
# SAPI Interface (Abstract Base Class)
# =============================================================================

class ISapiService(ABC):
    """Interface for the SayIntentions Cloud API (SAPI)"""

    @abstractmethod
    def connect(self, api_key: str) -> bool:
        """Authenticate/validate connection with the service"""
        pass

    @abstractmethod
    def get_status(self) -> str:
        """Get current connection status"""
        pass

    # Communication endpoints
    @abstractmethod
    def say_as(self, message: str, channel: Channel = Channel.COM1, 
               entity: Entity = Entity.ATC) -> SapiResponse:
        """Make an entity speak a message"""
        pass

    @abstractmethod
    def get_comms_history(self) -> SapiResponse:
        """Get communication history with audio URLs"""
        pass

    # Weather endpoints
    @abstractmethod
    def get_weather(self, icao: str) -> SapiResponse:
        """Get weather (ATIS, METAR, TAF) for an airport"""
        pass

    # Airport operations
    @abstractmethod
    def assign_gate(self, gate: str) -> SapiResponse:
        """Request a specific gate assignment"""
        pass

    @abstractmethod
    def get_parking(self) -> SapiResponse:
        """Get current assigned parking position"""
        pass

    # Flight management
    @abstractmethod
    def set_frequency(self, freq: str, channel: Channel = Channel.COM1) -> SapiResponse:
        """Set radio frequency"""
        pass

    @abstractmethod
    def set_pause(self, paused: bool) -> SapiResponse:
        """Pause/resume ATC simulation"""
        pass


# =============================================================================
# Live SAPI Implementation
# =============================================================================

class SapiService(ISapiService):
    """
    Production implementation of the SAPI interface.
    Communicates with the SayIntentions cloud backend via REST API.
    """
    
    BASE_URL = "https://apipri.sayintentions.ai/sapi"
    REQUEST_TIMEOUT = 10  # seconds
    
    def __init__(self, api_key: Optional[str] = None, config_path: Optional[str] = None):
        """
        Initialize the SAPI service.
        
        Args:
            api_key: API key for authentication. If not provided, reads from config.
            config_path: Path to config.ini. Defaults to project root.
        """
        self.logger = logging.getLogger("SapiService")
        self._connected = False
        self._api_key = api_key
        
        # Load config if api_key not provided
        if not self._api_key and config_path:
            self._load_config(config_path)
        elif not self._api_key:
            # Try default locations
            default_paths = [
                os.path.expanduser("~/.config/sayintentionsai/config.ini"),
                # From sapi_interface.py: client/src/core/ -> project root
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "config.ini"),
                # From cli.py: client/src/ -> project root  
                os.path.join(os.path.dirname(__file__), "..", "..", "config.ini"),
                # Current working directory
                "config.ini",
            ]
            for path in default_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    self._load_config(abs_path)
                    break
        
        # Create session for connection pooling
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "SayIntentionsML/1.0 (Linux)",
            "Accept": "application/json"
        })

    def _load_config(self, config_path: str):
        """Load API key from config file"""
        config = configparser.ConfigParser()
        config.read(config_path)
        if config.has_option("sapi", "api_key"):
            self._api_key = config.get("sapi", "api_key")
            self.logger.info(f"Loaded API key from {config_path}")

    def _make_request(self, endpoint: str, params: Optional[Dict] = None, 
                      method: str = "GET") -> SapiResponse:
        """
        Make a request to the SAPI endpoint.
        
        Args:
            endpoint: API endpoint (e.g., "getCommsHistory")
            params: Additional query parameters
            method: HTTP method (GET or POST)
            
        Returns:
            SapiResponse with success status and data/error
        """
        if not self._api_key:
            return SapiResponse(success=False, error="No API key configured")
        
        url = f"{self.BASE_URL}/{endpoint}"
        request_params = {"api_key": self._api_key}
        if params:
            request_params.update(params)
        
        try:
            if method.upper() == "GET":
                response = self._session.get(
                    url, 
                    params=request_params, 
                    timeout=self.REQUEST_TIMEOUT
                )
            else:
                response = self._session.post(
                    url, 
                    params=request_params, 
                    timeout=self.REQUEST_TIMEOUT
                )
            
            response.raise_for_status()
            
            # Try to parse JSON, fall back to text
            try:
                data = response.json()
            except ValueError:
                data = response.text
            
            return SapiResponse(
                success=True, 
                data=data, 
                status_code=response.status_code
            )
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Request timeout for {endpoint}")
            return SapiResponse(success=False, error="Request timeout")
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error for {endpoint}: {e}")
            return SapiResponse(
                success=False, 
                error=str(e), 
                status_code=e.response.status_code if e.response else 0
            )
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error for {endpoint}: {e}")
            return SapiResponse(success=False, error=str(e))

    # -------------------------------------------------------------------------
    # Connection Management
    # -------------------------------------------------------------------------

    def connect(self, api_key: Optional[str] = None) -> bool:
        """
        Validate connection by testing the API key.
        
        Args:
            api_key: Optional API key override
            
        Returns:
            True if connection successful
        """
        if api_key:
            self._api_key = api_key
        
        if not self._api_key:
            self.logger.error("No API key provided")
            return False
        
        # Test connection with getCommsHistory (lightweight endpoint)
        self.logger.info("Testing API connection...")
        response = self._make_request("getCommsHistory")
        
        if response.success:
            self._connected = True
            self.logger.info("✓ API connection successful")
            return True
        else:
            self._connected = False
            self.logger.error(f"✗ API connection failed: {response.error}")
            return False

    def get_status(self) -> str:
        """Get current connection status"""
        if not self._api_key:
            return "NO_API_KEY"
        return "CONNECTED" if self._connected else "DISCONNECTED"

    @property
    def is_connected(self) -> bool:
        """Check if currently connected"""
        return self._connected

    # -------------------------------------------------------------------------
    # Communication Endpoints
    # -------------------------------------------------------------------------

    def say_as(self, message: str, channel: Channel = Channel.COM1,
               entity: Entity = Entity.ATC) -> SapiResponse:
        """
        Make an entity speak a message.
        
        This is the primary way to send pilot transmissions to ATC.
        
        Args:
            message: The text message to speak
            channel: Radio channel (COM1, COM2, INTERCOM)
            entity: Who should speak (atc, copilot, crew, dispatcher)
            
        Returns:
            SapiResponse with result
        """
        params = {
            "message": message,
            "channel": channel.value,
            "entity": entity.value
        }
        
        self.logger.info(f"sayAs: [{channel.value}] {message[:50]}...")
        return self._make_request("sayAs", params)

    def get_comms_history(self) -> SapiResponse:
        """
        Get communication history with audio URLs.
        
        This is the **critical endpoint** for the native client.
        Returns all recent communications with downloadable audio file URLs.
        
        Returns:
            SapiResponse with data containing list of CommEntry objects
        """
        response = self._make_request("getCommsHistory")
        
        if response.success and response.data:
            # Parse the comm_history array into CommEntry objects
            raw_history = response.data.get("comm_history", [])
            entries = [CommEntry.from_dict(entry) for entry in raw_history]
            response.data = entries
            self.logger.debug(f"Retrieved {len(entries)} comm entries")
        
        return response

    # -------------------------------------------------------------------------
    # Weather Endpoints
    # -------------------------------------------------------------------------

    def get_weather(self, icao: str) -> SapiResponse:
        """
        Get weather information for an airport.
        
        Args:
            icao: ICAO airport code (e.g., "KTRK", "KSFO")
            
        Returns:
            SapiResponse with WeatherData
        """
        response = self._make_request("getWX", {"icao": icao})
        
        if response.success and response.data:
            response.data = WeatherData.from_dict(icao, response.data)
        
        return response

    def get_tfrs(self) -> SapiResponse:
        """
        Get Temporary Flight Restrictions (TFRs) as GeoJSON.
        
        Returns:
            SapiResponse with GeoJSON data
        """
        return self._make_request("getTFRs")

    # -------------------------------------------------------------------------
    # Airport Operations
    # -------------------------------------------------------------------------

    def assign_gate(self, gate: str) -> SapiResponse:
        """
        Request assignment to a specific gate.
        
        Args:
            gate: Gate identifier (e.g., "A12", "B5")
            
        Returns:
            SapiResponse with result
        """
        return self._make_request("assignGate", {"gate": gate})

    def get_parking(self) -> SapiResponse:
        """
        Get current assigned parking position.
        
        Returns:
            SapiResponse with ParkingInfo (lat/lon/hdg)
        """
        response = self._make_request("getParking")
        
        if response.success and response.data:
            response.data = ParkingInfo.from_dict(response.data)
        
        return response

    # -------------------------------------------------------------------------
    # Flight Management
    # -------------------------------------------------------------------------

    def set_frequency(self, freq: str, channel: Channel = Channel.COM1) -> SapiResponse:
        """
        Set radio frequency.
        
        Args:
            freq: Frequency string (e.g., "120.575")
            channel: Radio channel to set
            
        Returns:
            SapiResponse with result
        """
        return self._make_request("setFreq", {
            "freq": freq,
            "channel": channel.value
        })

    def set_pause(self, paused: bool) -> SapiResponse:
        """
        Pause or resume ATC simulation.
        
        Args:
            paused: True to pause, False to resume
            
        Returns:
            SapiResponse with result
        """
        return self._make_request("setPause", {"paused": str(paused).lower()})

    def set_variable(self, name: str, value: Any) -> SapiResponse:
        """
        Set a simulator variable.
        
        Args:
            name: Variable name
            value: Variable value
            
        Returns:
            SapiResponse with result
        """
        return self._make_request("setVar", {"name": name, "value": str(value)})

    # -------------------------------------------------------------------------
    # VATSIM Integration
    # -------------------------------------------------------------------------

    def get_vatsim(self) -> SapiResponse:
        """
        Get VATSIM traffic data.
        
        Returns:
            SapiResponse with VATSIM data
        """
        return self._make_request("getVATSIM")

    # -------------------------------------------------------------------------
    # Audio Download Helper
    # -------------------------------------------------------------------------

    def download_audio(self, url: str, save_path: Optional[str] = None) -> Optional[bytes]:
        """
        Download an audio file from the given URL.
        
        Args:
            url: Full URL to the audio file (e.g., S3 URL from comm history)
            save_path: Optional path to save the file
            
        Returns:
            Audio data as bytes, or None on failure
        """
        try:
            response = self._session.get(url, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            audio_data = response.content
            
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(audio_data)
                self.logger.info(f"Audio saved to {save_path}")
            
            return audio_data
            
        except Exception as e:
            self.logger.error(f"Failed to download audio: {e}")
            return None


# =============================================================================
# Mock Implementation (for testing without API)
# =============================================================================

class MockSapiService(ISapiService):
    """Mock implementation for development without an API Key"""
    
    def __init__(self):
        self._connected = False
        self.logger = logging.getLogger("MockSapi")
        self._mock_history: List[CommEntry] = []

    def connect(self, api_key: str = "") -> bool:
        self.logger.info(f"Mock connecting with key: {api_key[:4]}...")
        time.sleep(0.5)  # Simulate network delay
        self._connected = True
        return True

    def get_status(self) -> str:
        return "CONNECTED (MOCK)" if self._connected else "DISCONNECTED"

    def say_as(self, message: str, channel: Channel = Channel.COM1,
               entity: Entity = Entity.ATC) -> SapiResponse:
        self.logger.info(f"Mock sayAs: [{channel.value}] {message}")
        # Add mock response to history
        self._mock_history.append(CommEntry(
            station_name="Mock Tower",
            ident="MOCK",
            frequency="123.45",
            incoming_message=message,
            outgoing_message="Roger, mock acknowledged.",
            atc_url=None
        ))
        return SapiResponse(success=True, data={"status": "ok"})

    def get_comms_history(self) -> SapiResponse:
        return SapiResponse(success=True, data=self._mock_history)

    def get_weather(self, icao: str) -> SapiResponse:
        mock_wx = WeatherData(
            icao=icao,
            atis="Mock ATIS information",
            metar=f"{icao} 231856Z 27008KT 10SM FEW200 18/M02 A3012",
            taf=f"{icao} TAF mock data"
        )
        return SapiResponse(success=True, data=mock_wx)

    def assign_gate(self, gate: str) -> SapiResponse:
        return SapiResponse(success=True, data={"gate": gate, "status": "assigned"})

    def get_parking(self) -> SapiResponse:
        return SapiResponse(success=True, data=ParkingInfo(
            gate="A1", latitude=39.327, longitude=-120.140, heading=270.0
        ))

    def set_frequency(self, freq: str, channel: Channel = Channel.COM1) -> SapiResponse:
        return SapiResponse(success=True, data={"freq": freq, "channel": channel.value})

    def set_pause(self, paused: bool) -> SapiResponse:
        return SapiResponse(success=True, data={"paused": paused})


# =============================================================================
# Factory Function
# =============================================================================

def create_sapi_service(use_mock: bool = False, 
                        api_key: Optional[str] = None,
                        config_path: Optional[str] = None) -> ISapiService:
    """
    Factory function to create the appropriate SAPI service.
    
    Args:
        use_mock: If True, return mock service for testing
        api_key: API key for live service
        config_path: Path to config.ini for live service
        
    Returns:
        ISapiService implementation
    """
    if use_mock:
        return MockSapiService()
    return SapiService(api_key=api_key, config_path=config_path)
