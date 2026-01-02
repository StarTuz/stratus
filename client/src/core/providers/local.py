from typing import Tuple, List, Optional, Any
from .base import IATCProvider, ATCResponse
from ..sim_data import SimDataInterface
import dbus
import logging
import time

class LocalSpeechProvider(IATCProvider):
    """
    Provider for SpeechD-NG (Local AI).
    Uses D-Bus to communicate with org.speech.Service.
    """
    
    BUS_NAME = "org.speech.Service"
    OBJECT_PATH = "/org/speech/Service"
    INTERFACE = "org.speech.Service"

    def __init__(self):
        self.logger = logging.getLogger("LocalSpeechProvider")
        self.bus = None
        self.proxy = None
        self.connected = False
        self.sim_data = SimDataInterface()
        self.variables = {}
        self.frequencies = {"COM1": "---", "COM2": "---"}

    def connect(self) -> bool:
        try:
            self.bus = dbus.SessionBus()
            self.proxy = self.bus.get_object(self.BUS_NAME, self.OBJECT_PATH)
            # Ping to verify
            self.proxy.Ping(dbus_interface=self.INTERFACE)
            self.connected = True
            self.logger.info("Connected to SpeechD-NG via D-Bus")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to SpeechD-NG: {e}")
            self.connected = False
            return False

    def disconnect(self):
        self.bus = None
        self.proxy = None
        self.connected = False

    @property
    def is_connected(self) -> bool:
        return self.connected

    def get_status(self) -> str:
        return "CONNECTED (LOCAL)" if self.connected else "DISCONNECTED"

    def say(self, text: str, voice: str = "", channel: str = "") -> ATCResponse:
        if not self.connected:
            return ATCResponse(False, error="Not connected")
        try:
            if channel:
                # Speak to specific channel (left/right/surround)
                self.proxy.SpeakChannel(text, voice, channel, dbus_interface=self.INTERFACE, timeout=10)
            elif voice:
                self.proxy.SpeakVoice(text, voice, dbus_interface=self.INTERFACE, timeout=10)
            else:
                self.proxy.Speak(text, dbus_interface=self.INTERFACE, timeout=10)
            return ATCResponse(True)
        except Exception as e:
            return ATCResponse(False, error=str(e))

    def think(self, context: str) -> ATCResponse:
        """Query the Local Brain"""
        if not self.connected:
            return ATCResponse(False, error="Not connected")
            
        # Build context-rich prompt
        full_context = self._build_context(context)
        
        try:
            # AI generation can take a long time, use 10s timeout
            response = self.proxy.Think(full_context, dbus_interface=self.INTERFACE, timeout=10)
            return ATCResponse(True, data=str(response))
        except dbus.exceptions.DBusException as e:
            error_str = str(e)
            if "NoReply" in error_str or "Timeout" in error_str:
                return ATCResponse(False, error="Engine Latency: The speech engine timed out (>10s). Use a faster model or Wyoming backend.")
            return ATCResponse(False, error=error_str)
        except Exception as e:
            return ATCResponse(False, error=str(e))

    def _build_context(self, user_context: str) -> str:
        """Construct a context-rich prompt using sim telemetry.
        
        The user_context is expected to contain the full prompt.
        We append simulator state as reference data.
        """
        t = self.sim_data.read_telemetry()
        
        # Build simulator state reference
        if t.connected:
            sim_state = f"""
[AIRCRAFT STATUS]
- Callsign: {t.tail_number}
- Type: {t.icao_type}
- Position: {t.latitude:.4f}, {t.longitude:.4f}
- Altitude: {int(t.altitude_msl)}ft MSL
- Heading: {int(t.heading_mag)}°
- Speed: {int(t.ias)} KIAS
- On Ground: {'Yes' if t.on_ground else 'No'}
- COM1: {t.com1.active}
- COM2: {t.com2.active}
- Transponder: {t.transponder.code}
"""
        else:
            sim_state = "\n[AIRCRAFT STATUS: Simulator Disconnected]\n"

        # Return prompt WITH sim state appended as context
        return f"{user_context}\n{sim_state}"


    def listen(self, timeout_sec: int = 5) -> ATCResponse:
        """Listen using VAD (Voice Activity Detection)"""
        if not self.connected:
            return ATCResponse(False, error="Not connected")
        try:
            # ListenVad handles silence detection automatically
            # The daemon might take a few seconds to process VAD and transcribe.
            # Using 10s timeout as requested by user.
            text = self.proxy.ListenVad(dbus_interface=self.INTERFACE, timeout=10)
            return ATCResponse(True, data=str(text))
        except dbus.exceptions.DBusException as e:
            error_str = str(e)
            if "NoReply" in error_str or "Timeout" in error_str:
                return ATCResponse(False, error="Engine Latency: STT timed out (>10s). Check model configuration.")
            return ATCResponse(False, error=error_str)
        except Exception as e:
            return ATCResponse(False, error=str(e))
            
    # --- Compatibility Methods ---
    
    def get_comms_history(self, lat: float = None, lon: float = None) -> ATCResponse:
        """
        Return history. For Local AI, we might not have a history API yet.
        Returning empty list to satisfy UI polling.
        """
        return ATCResponse(True, data=[])

    def set_variable(self, name: str, value: str, unit: str = "") -> bool:
        """
        Set a context variable for the AI.
        """
        val = f"{value} {unit}".strip()
        self.variables[name] = val
        return True

    def set_frequency(self, frequency: str, channel: str = "COM1") -> ATCResponse:
        """
        Set active frequency for a channel.
        """
        self.frequencies[channel] = frequency
        return ATCResponse(True)

    def say_as(self, text: str, entity: str = "pilot", channel: str = "COM1") -> ATCResponse:
        """
        Legacy compatibility for 'say_as'. Maps to 'say'.
        'entity' and 'channel' are ignored or mapped to channel if possible.
        """
        # Map COM1/COM2 to left/right if desired, or just use default
        return self.say(text)

    # --- Brain Management ---
    
    def get_brain_status(self) -> Tuple[bool, str, List[str]]:
        """Get status of the local AI brain."""
        if not self.connected:
            return False, "Disconnected", []
        try:
            is_running, model, available = self.proxy.GetBrainStatus(dbus_interface=self.INTERFACE)
            return bool(is_running), str(model), [str(m) for m in available]
        except Exception:
            return False, "Error", []

    def manage_brain(self, action: str, param: str = "") -> bool:
        """Perform action on local AI brain (start, stop, pull)."""
        if not self.connected:
            return False
        try:
            return bool(self.proxy.ManageBrain(action, param, dbus_interface=self.INTERFACE))
        except Exception:
            return False

