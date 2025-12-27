"""
Simple Audio Player using external player

Uses platform-appropriate audio player as subprocess:
- Linux: mpv (preferred) or ffplay
- macOS: afplay (built-in)

This avoids all Python audio threading issues.
"""

import logging
import subprocess
import threading
import queue
import platform
import shutil
from pathlib import Path
from typing import Optional, Callable, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


def detect_audio_player() -> Tuple[str, List[str]]:
    """
    Detect the best available audio player for the current platform.
    
    Returns:
        Tuple of (player_name, base_command_args)
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        # afplay is built-in on macOS
        return ("afplay", ["afplay"])
    
    elif system == "Linux":
        # Try mpv first (best compatibility), then ffplay
        if shutil.which("mpv"):
            return ("mpv", ["mpv", "--no-video", "--really-quiet"])
        elif shutil.which("ffplay"):
            return ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"])
        elif shutil.which("paplay"):
            # PulseAudio player (needs WAV, so less ideal for MP3)
            return ("paplay", ["paplay"])
        else:
            logger.warning("No audio player found! Install mpv: sudo pacman -S mpv")
            return ("none", [])
    
    elif system == "Windows":
        # Windows - could use PowerShell or wmplayer
        # For now, try ffplay if available
        if shutil.which("ffplay"):
            return ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"])
        else:
            return ("none", [])
    
    return ("none", [])


class PlayerState(Enum):
    """Current state of the audio player."""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPING = "stopping"


@dataclass
class AudioPlayerConfig:
    """Configuration for the audio player."""
    volume: float = 1.0
    device: Optional[str] = None
    sample_rate: int = 44100
    channels: int = 1
    block_size: int = 2048


@dataclass
class QueuedAudio:
    """An audio file queued for playback."""
    file_path: Path
    on_start: Optional[Callable[[], None]] = None
    on_complete: Optional[Callable[[], None]] = None
    metadata: dict = field(default_factory=dict)


class AudioPlayer:
    """
    Cross-platform audio player using external subprocess.
    
    Automatically detects and uses the best available player:
    - Linux: mpv (preferred) or ffplay
    - macOS: afplay (built-in)
    
    This approach completely decouples audio playback from Python,
    preventing any GIL-related freezes.
    """
    
    def __init__(self, config: Optional[AudioPlayerConfig] = None):
        self.config = config or AudioPlayerConfig()
        self._state = PlayerState.IDLE
        self._queue: queue.Queue[QueuedAudio] = queue.Queue()
        self._current_audio: Optional[QueuedAudio] = None
        self._current_process: Optional[subprocess.Popen] = None
        self._stop_event = threading.Event()
        self._player_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self._on_state_change: Optional[Callable[[PlayerState], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        
        # Detect platform-appropriate audio player
        self._player_name, self._player_cmd = detect_audio_player()
        
        if self._player_name == "none":
            logger.error("No audio player available!")
        else:
            logger.info(f"AudioPlayer initialized (using {self._player_name}, volume={self.config.volume})")
    
    @property
    def state(self) -> PlayerState:
        return self._state
    
    @state.setter
    def state(self, new_state: PlayerState):
        if self._state != new_state:
            self._state = new_state
            logger.debug(f"Player state: {new_state.value}")
            if self._on_state_change:
                try:
                    self._on_state_change(new_state)
                except Exception as e:
                    logger.error(f"State change callback error: {e}")
    
    def set_state_callback(self, callback: Callable[[PlayerState], None]):
        self._on_state_change = callback
    
    def set_error_callback(self, callback: Callable[[str], None]):
        self._on_error = callback
    
    def set_volume(self, volume: float):
        self.config.volume = max(0.0, min(1.0, volume))
        logger.debug(f"Volume set to {self.config.volume}")
    
    def get_volume(self) -> float:
        return self.config.volume
    
    def queue_file(self, file_path: Path, 
                   on_start: Optional[Callable[[], None]] = None,
                   on_complete: Optional[Callable[[], None]] = None,
                   metadata: Optional[dict] = None) -> bool:
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        audio = QueuedAudio(
            file_path=file_path,
            on_start=on_start,
            on_complete=on_complete,
            metadata=metadata or {}
        )
        
        self._queue.put(audio)
        logger.debug(f"Queued: {file_path.name} (queue size: {self._queue.qsize()})")
        
        self._ensure_player_running()
        return True
    
    def queue_size(self) -> int:
        return self._queue.qsize()
    
    def clear_queue(self):
        cleared = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                cleared += 1
            except queue.Empty:
                break
        logger.info(f"Queue cleared ({cleared} items)")
    
    def play(self):
        if self._state == PlayerState.PAUSED:
            # Can't unpause mpv easily, just note it
            self.state = PlayerState.PLAYING
            logger.info("Playback resumed (note: mpv subprocess continues)")
    
    def pause(self):
        if self._state == PlayerState.PLAYING:
            self.state = PlayerState.PAUSED
            logger.info("Playback paused (note: mpv subprocess continues)")
    
    def stop(self):
        logger.info("Stopping playback")
        self._stop_event.set()
        
        # Kill current mpv process if running
        if self._current_process:
            try:
                self._current_process.terminate()
                self._current_process.wait(timeout=1)
            except:
                try:
                    self._current_process.kill()
                except:
                    pass
            self._current_process = None
        
        self.clear_queue()
        
        if self._player_thread and self._player_thread.is_alive():
            self._player_thread.join(timeout=2.0)
        
        self.state = PlayerState.IDLE
    
    def skip(self):
        logger.info("Skipping current audio")
        if self._current_process:
            try:
                self._current_process.terminate()
            except:
                pass
    
    def _ensure_player_running(self):
        with self._lock:
            if self._player_thread is None or not self._player_thread.is_alive():
                self._stop_event.clear()
                self._player_thread = threading.Thread(
                    target=self._player_loop,
                    name="MpvPlayerThread",
                    daemon=True
                )
                self._player_thread.start()
                logger.debug("Player thread started")
    
    def _player_loop(self):
        logger.debug("Player loop started")
        
        while not self._stop_event.is_set():
            try:
                try:
                    audio = self._queue.get(timeout=0.5)
                except queue.Empty:
                    if self._queue.empty():
                        self.state = PlayerState.IDLE
                    continue
                
                self._current_audio = audio
                self._play_file(audio)
                self._current_audio = None
                
            except Exception as e:
                logger.error(f"Player loop error: {e}")
                if self._on_error:
                    self._on_error(str(e))
        
        logger.debug("Player loop exited")
        self.state = PlayerState.IDLE
    
    def _play_file(self, audio: QueuedAudio):
        file_path = audio.file_path
        logger.info(f"Playing: {file_path.name}")
        
        try:
            # Notify start callback
            if audio.on_start:
                try:
                    audio.on_start()
                except Exception as e:
                    logger.error(f"on_start callback error: {e}")
            
            self.state = PlayerState.PLAYING
            
            # Build command based on detected player
            if self._player_name == "none":
                raise RuntimeError("No audio player available")
            
            # Start with base command
            cmd = list(self._player_cmd)
            
            # Add volume control based on player type
            volume_percent = int(self.config.volume * 100)
            
            if self._player_name == "mpv":
                cmd.append(f'--volume={volume_percent}')
            elif self._player_name == "ffplay":
                # ffplay uses -volume 0-100
                cmd.extend(['-volume', str(volume_percent)])
            elif self._player_name == "afplay":
                # afplay uses -v 0.0-1.0
                cmd.extend(['-v', str(self.config.volume)])
            # paplay doesn't have easy volume control
            
            # Add the file path
            cmd.append(str(file_path))
            
            logger.debug(f"Running: {' '.join(cmd)}")
            
            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for playback to complete (checking for stop event)
            while self._current_process.poll() is None:
                if self._stop_event.is_set():
                    self._current_process.terminate()
                    break
                self._stop_event.wait(0.1)
            
            self._current_process = None
            
            logger.debug(f"Finished: {file_path.name}")
            
            # Notify complete callback
            if audio.on_complete:
                try:
                    audio.on_complete()
                except Exception as e:
                    logger.error(f"on_complete callback error: {e}")
                    
        except Exception as e:
            error_msg = f"Playback error for {file_path.name}: {e}"
            logger.error(error_msg)
            if self._on_error:
                self._on_error(error_msg)
    
    def list_devices(self):
        """List available audio output devices."""
        return [{'index': 0, 'name': f'Default ({self._player_name})', 'is_default': True}]
    
    def __del__(self):
        self.stop()
