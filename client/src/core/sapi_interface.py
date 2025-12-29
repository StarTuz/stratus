"""
Stratus API (SAPI) Interface Module

This module provides a complete Python interface to the Stratus cloud API.
It handles all REST endpoint communication for the native Linux/Mac client.

Base URL: https://apipri.stratus.ai/sapi/
Authentication: API key as URL parameter (?api_key=XXX)
Documentation: https://p2.stratus.ai/p2/docs/
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


class ATCMode(Enum):
    """ATC experience modes - affects verbosity and UI aids"""
    STUDENT = "student"    # Slower, explicit instructions, full guidance
    STANDARD = "standard"  # True-to-life ATC experience
    PRO = "pro"            # Advanced - no UI aids, realistic


class Entity(Enum):
    """Entity types that can speak"""
    ATC = "atc"
    COPILOT = "copilot"
    CREW = "crew"              # Cabin crew announcements
    DISPATCHER = "dispatcher"
    TOUR_GUIDE = "tourguide"   # VFR landmarks and points of interest
    MENTOR = "mentor"          # Virtual flight instructor - answers questions


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

class ISapiService:

    """Interface for the Stratus Cloud API (SAPI)"""

    def connect(self, api_key: str) -> bool:
        """Authenticate/validate connection with the service"""
        pass

    def get_status(self) -> str:
        """Get current connection status"""
        pass

    # Communication endpoints
    def say_as(self, message: str, channel: Channel = Channel.COM1, 
               entity: Entity = Entity.ATC) -> SapiResponse:
        """Make an entity speak a message"""
        pass

    def get_comms_history(self, lat: Optional[float] = None, lon: Optional[float] = None) -> SapiResponse:
        """Get communication history with audio URLs."""
        pass


    # Weather endpoints
    def get_weather(self, icao: str) -> SapiResponse:
        """Get weather (ATIS, METAR, TAF) for an airport"""
        pass

    # Airport operations
    def assign_gate(self, gate: str, icao: Optional[str] = None) -> SapiResponse:
        """Request a specific gate assignment"""
        pass


    def get_parking(self) -> SapiResponse:
        """Get current assigned parking position"""
        pass

    def reset_session(self, icao: str = "F70") -> SapiResponse:
        """Force a session state refresh"""
        pass



    # Flight management
    def set_frequency(self, freq: str, channel: Channel = Channel.COM1) -> SapiResponse:
        """Set radio frequency"""
        pass

    def set_pause(self, paused: bool) -> SapiResponse:
        """Pause/resume ATC simulation"""
        pass


# =============================================================================
# Live SAPI Implementation
# =============================================================================

class SapiService(ISapiService):
    """
    Production implementation of the SAPI interface.
    Communicates with the Stratus cloud backend via REST API.
    """
    
    BASE_URL = "https://apipri.stratus.ai/sapi"
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
                os.path.expanduser("~/.config/stratusai/config.ini"),
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
            "User-Agent": "StratusML/1.0 (Linux)",
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
                      method: str = "GET", json_data: Optional[Dict] = None) -> SapiResponse:
        """
        Make a request to the SAPI endpoint.
        
        Args:
            endpoint: API endpoint (e.g., "getCommsHistory")
            params: Additional query parameters
            method: HTTP method (GET or POST)
            json_data: JSON payload for POST requests
            
        Returns:
            SapiResponse with success status and data/error
        """
        if not self._api_key:
            return SapiResponse(False, error="API key not configured")
            
        if endpoint.startswith("http"):
            url = endpoint
        else:
            url = f"{self.BASE_URL}/{endpoint}"
        
        # SAPI prefers the X-API-Key header over query parameters
        headers = {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json"
        }
        
        # But we'll keep the param as a fallback for older endpoints
        request_params = {"api_key": self._api_key}
        if params:
            request_params.update(params)
            
        try:
            if method.upper() == "GET":
                response = self._session.get(
                    url, 
                    params=request_params, 
                    headers=headers,
                    timeout=self.REQUEST_TIMEOUT
                )
            else:
                response = self._session.post(
                    url, 
                    params=request_params, 
                    headers=headers,
                    json=json_data,
                    timeout=self.REQUEST_TIMEOUT
                )
            
            # Log the request for debugging telemetry issues
            self.logger.debug(f"SAPI {method} {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict) and "error" in data:
                        self.logger.warning(f"SAPI Logical Error: {data['error']}")
                        return SapiResponse(False, error=data['error'], status_code=200)
                    return SapiResponse(True, data=data, status_code=200)
                except ValueError:
                    # Some endpoints might return empty or non-JSON success
                    return SapiResponse(True, status_code=200)
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", f"HTTP {response.status_code}")
                except:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                return SapiResponse(False, error=error_msg, status_code=response.status_code)
                
        except requests.exceptions.RequestException as e:
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

    def get_comms_history(self, lat: Optional[float] = None, lon: Optional[float] = None) -> SapiResponse:
        """
        Get communication history with audio URLs.
        
        This is the **critical endpoint** for the native client.
        Returns all recent communications with downloadable audio file URLs.
        
        Args:
            lat: Current latitude
            lon: Current longitude
            
        Returns:
            SapiResponse with data containing list of CommEntry objects
        """
        params = {}
        if lat is not None:
            params["lat"] = str(lat)
        if lon is not None:
            params["lon"] = str(lon)
            
        response = self._make_request("getCommsHistory", params)

        
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

    def assign_gate(self, gate: str, icao: Optional[str] = None) -> SapiResponse:
        """
        Request assignment to a specific gate.
        
        Args:
            gate: Gate identifier (e.g., "A12", "B5")
            icao: Optional ICAO code to force location update
            
        Returns:
            SapiResponse with result
        """
        params = {"gate": gate}
        if icao:
            params["icao"] = icao
            # P2D specific endpoint for forcing location re-indexing
            url = "https://p2d.stratus.ai/p2d/api/gateAssign"
            headers = {"X-API-Key": self._api_key, "Content-Type": "application/json"}
            payload = {"api_key": self._api_key, "icao": icao, "gate": gate}
            try:
                self.logger.info(f"Forcing location via gateAssign: {icao} @ {gate}")
                self._session.post(url, json=payload, headers=headers, timeout=5)
            except Exception as e:
                self.logger.warning(f"p2d gateAssign failed: {e}")

        return self._make_request("assignGate", params)

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

    def reset_session(self, icao: str = "F70") -> SapiResponse:

        """
        Force a session state refresh using the gateAssign and pause toggle tricks.
        
        Args:
            icao: Target ICAO code (default F70)
            
        Returns:
            SapiResponse indicating success
        """
        self.logger.info(f"Performing session reset for {icao}...")
        
        # 1. Force location via gateAssign
        self.assign_gate("RAMP 1", icao=icao)
        
        # 2. Toggle pause (1 then 0) to trigger sidecar refresh
        self.set_pause(True)
        time.sleep(0.5)
        self.set_pause(False)
        
        return SapiResponse(True)

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

    def set_variable(self, var: str, value: Any, category: str = "A") -> SapiResponse:

        """
        Set a simulator variable via the REST API.
        
        Args:
            var: Variable name (e.g. "PLANE LATITUDE")
            value: Variable value
            category: Variable category (default "L")
            
        Returns:
            SapiResponse with result
        """
        return self._make_request("setVar", {
            "var": var, 
            "value": str(value),
            "category": category
        })

    def update_telemetry(self, t: Dict[str, Any]) -> SapiResponse:
        """
        Update the server with current aircraft telemetry.
        
        This translates the native telemetry format to the EXHAUSTIVE 
        SimAPI format required by the SAPI cloud brain.
        
        Args:
            t: Dictionary containing aircraft state (position, radios, etc)
            
        Returns:
            SapiResponse
        """
        # SAPI expects specific MSFS variable names. 
        # Many of these are "Non-Negotiable" according to SimAPI spec.
        on_ground = 1 if t.get("on_ground") else 0
        
        # Use Category 'A' (Aircraft) for physical location variables
        # formatted to 6 decimal places for cloud precision
        lat_val = t.get("latitude", 0.0)
        lon_val = t.get("longitude", 0.0)
        lat_str = f"{lat_val:.6f}"
        lon_str = f"{lon_val:.6f}"

        msfs_data = {
            "sim": {
                "variables": {
                    # Essentials
                    "PLANE LATITUDE": lat_str,
                    "PLANE LONGITUDE": lon_str,
                    "PLANE_LATITUDE": lat_str,
                    "PLANE_LONGITUDE": lon_str,
                    "PLANE ALTITUDE": t.get("altitude_msl", 0.0),
                    "INDICATED ALTITUDE": t.get("altitude_msl", 0.0),

                    "PLANE ALT ABOVE GROUND MINUS CG": 0 if on_ground else t.get("altitude_agl", 0.0),
                    "SIM ON GROUND": on_ground,
                    
                    # Heading & Attitude
                    "MAGNETIC COMPASS": t.get("heading_mag", 0.0),
                    "PLANE HEADING DEGREES TRUE": t.get("heading_true", t.get("heading_mag", 0.0)),
                    "MAGVAR": 12, # Realistic default or calculated
                    "PLANE PITCH DEGREES": t.get("pitch", 0.0),
                    "PLANE BANK DEGREES": t.get("roll", 0.0),
                    
                    # Speed
                    "AIRSPEED INDICATED": t.get("ias", 0.0),
                    "AIRSPEED TRUE": t.get("groundspeed", 0.0),
                    "VERTICAL SPEED": t.get("vertical_speed", 0.0),
                    "WHEEL RPM:1": 100 if (on_ground and t.get("groundspeed", 0.0) > 1) else 0,
                    "WHEEL RPM:0": 100 if (on_ground and t.get("groundspeed", 0.0) > 1) else 0,
                    
                    # Radios (CRITICAL)
                    "COM ACTIVE FREQUENCY:1": self._parse_freq(t.get("com1_active")),
                    "COM STANDBY FREQUENCY:1": self._parse_freq(t.get("com1_standby")),
                    "COM RECEIVE:1": 1,
                    "COM TRANSMIT:1": 1,
                    "COM ACTIVE FREQUENCY:2": self._parse_freq(t.get("com2_active")),
                    "COM STANDBY FREQUENCY:2": self._parse_freq(t.get("com2_standby")),
                    "COM RECEIVE:2": 0,
                    "COM TRANSMIT:2": 0,
                    "COM VOLUME:1": 80,
                    "COM VOLUME:2": 80,
                    "CIRCUIT COM ON:1": 1,
                    "CIRCUIT COM ON:2": 1,
                    "ELECTRICAL MASTER BATTERY:0": 1,
                    
                    # Transponder
                    "TRANSPONDER CODE:1": int(t.get("transponder_code", "1200")),
                    "TRANSPONDER STATE:1": self._map_xpdr_mode(t.get("transponder_mode", "STBY")),
                    "TRANSPONDER IDENT": 0,
                    
                    # Performance Context
                    "ENGINE TYPE": 0, # Piston
                    "TOTAL WEIGHT": 2500,
                    "TITLE": t.get("tail_number", "Native Client"),
                    "ATC MODEL": t.get("icao_type", "C172"),
                    "LOCAL TIME": time.time() % 86400,
                    "ZULU TIME": time.time() % 86400
                },
                "exe": "StratusML.exe",
                "simapi_version": "1.0",
                "name": "X-Plane 12 (Native)",
                "version": "1.0.0",
                "adapter_version": "1.0.0"
            }
        }
        
        # Use the SIMAPI subdomain for telemetry ingestion
        return self._make_request("https://apipri.stratus.ai/simapi/v1/input", method="POST", json_data=msfs_data)

    def _parse_freq(self, freq_str: Any) -> float:
        """Helper to parse frequency string to float."""
        if not freq_str or freq_str == "---" or freq_str == "OFF":
            return 0.0
        try:
            return float(freq_str)
        except (ValueError, TypeError):
            return 0.0

    def _map_xpdr_mode(self, mode_str: str) -> int:
        """Map X-Plane transponder mode to MSFS transponder state."""
        # MSFS: 0:Off, 1:Standby, 2:Test, 3:On, 4:Alt
        mode_map = {
            "OFF": 0,
            "STBY": 1,
            "TEST": 2,
            "ON": 3,
            "ALT": 4
        }
        return mode_map.get(mode_str.upper(), 1)


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

    def get_comms_history(self, lat: Optional[float] = None, lon: Optional[float] = None) -> SapiResponse:
        self.logger.debug(f"Mock getCommsHistory (Pos: {lat}, {lon})")
        return SapiResponse(success=True, data=self._mock_history)


    def get_weather(self, icao: str) -> SapiResponse:
        mock_wx = WeatherData(
            icao=icao,
            atis="Mock ATIS information",
            metar=f"{icao} 231856Z 27008KT 10SM FEW200 18/M02 A3012",
            taf=f"{icao} TAF mock data"
        )
        return SapiResponse(success=True, data=mock_wx)

    def assign_gate(self, gate: str, icao: Optional[str] = None) -> SapiResponse:
        self.logger.info(f"Mock assignGate: {gate} (ICAO: {icao})")
        return SapiResponse(success=True, data={"gate": gate, "icao": icao, "status": "assigned"})

    def get_parking(self) -> SapiResponse:
        return SapiResponse(success=True, data=ParkingInfo(
            gate="A1", latitude=39.327, longitude=-120.140, heading=270.0
        ))

    def reset_session(self, icao: str = "F70") -> SapiResponse:
        self.logger.info(f"Mock resetSession: {icao}")
        return SapiResponse(True)


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
