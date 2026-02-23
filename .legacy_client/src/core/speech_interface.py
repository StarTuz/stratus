"""
Speech Interface for StratusATC
Wraps the SpeechD-NG D-Bus service for TTS and STT functionality.
"""

import logging
import dbus
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

SERVICE_NAME = 'org.speech.Service'
OBJECT_PATH = '/org/speech/Service'
INTERFACE_NAME = 'org.speech.Service'

class SpeechInterface:
    """Interface to SpeechD-NG daemon via D-Bus."""
    
    def __init__(self):
        self._bus = None
        self._interface = None
        self._available = False
        self._connect()
        
    def _connect(self):
        """Establish connection to the D-Bus service."""
        try:
            self._bus = dbus.SessionBus()
            # Check if service is running
            if not self._bus.name_has_owner(SERVICE_NAME):
                logger.warning(f"SpeechD-NG service {SERVICE_NAME} not found on session bus")
                self._available = False
                return
                
            obj = self._bus.get_object(SERVICE_NAME, OBJECT_PATH)
            self._interface = dbus.Interface(obj, INTERFACE_NAME)
            
            # Test connection with Ping
            response = self._interface.Ping(timeout=30)
            if response == "pong":
                self._available = True
                logger.info("Connected to SpeechD-NG successfully")
            else:
                self._available = False
                logger.error(f"SpeechD-NG Ping failed: {response}")
                
        except Exception as e:
            logger.error(f"Failed to connect to SpeechD-NG: {e}")
            self._available = False

    @property
    def is_available(self) -> bool:
        """Check if speech service is available."""
        # Re-check connection if it was down
        if not self._available:
            self._connect()
        return self._available

    def speak(self, text: str, voice: Optional[str] = None) -> bool:
        """
        Speak text using TTS.
        
        Args:
            text: Text to speak
            voice: Optional voice ID
        """
        if not self.is_available:
            return False
            
        try:
            if voice:
                self._interface.SpeakVoice(text, voice, timeout=10)
            else:
                self._interface.Speak(text, timeout=10)
            return True
        except dbus.exceptions.DBusException as e:
            error_str = str(e)
            if "NoReply" in error_str or "Timeout" in error_str:
                logger.error("Engine Latency: TTS timed out (>10s).")
            else:
                logger.error(f"D-Bus Error: {e}")
            return False
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            return False

    def listen_vad(self) -> Optional[str]:
        """
        Listen with Voice Activity Detection (VAD).
        This blocks until speech completes or timeout.
        
        Returns:
            Transcribed text, or None if error/silence.
        """
        if not self.is_available:
            return None
            
        try:
            logger.info("Listening for speech (VAD)...")
            # ListenVad can take a while. AI/Vosk might take time to initialize.
            # Use 10s timeout as requested by user.
            text = self._interface.ListenVad(timeout=10)
            logger.info(f"Transcribed: '{text}'")
            return str(text) if text else None
        except dbus.exceptions.DBusException as e:
            error_str = str(e)
            if "NoReply" in error_str or "Timeout" in error_str:
                logger.error("Engine Latency: STT timed out (>10s). Check model configuration.")
            else:
                logger.error(f"D-Bus Error: {e}")
            return None
        except Exception as e:
            logger.error(f"STT Error: {e}")
            return None

    def get_version(self) -> str:
        """Get daemon version."""
        if not self.is_available:
            return "Unknown"
        try:
            return str(self._interface.GetVersion())
        except:
            return "Unknown"
