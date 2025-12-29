"""
Audio Handler Module

High-level interface for downloading and playing ATC audio responses.
Combines the AudioDownloader and AudioPlayer for seamless operation.

Downloads are performed in background threads to prevent UI freezing.
"""

import logging
import threading
from pathlib import Path
from typing import Optional, Callable, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from .downloader import AudioDownloader, DownloadResult
from .player import AudioPlayer, AudioPlayerConfig, PlayerState

logger = logging.getLogger(__name__)


@dataclass
class AudioQueueItem:
    """Represents an audio item to be played."""
    url: str
    station_name: str = ""
    frequency: str = ""
    message: str = ""
    # Internal tracking
    download_result: Optional[DownloadResult] = None


class AudioHandler:
    """
    High-level audio handler for Stratus ATC responses.
    
    Manages downloading audio from URLs and playing them in sequence.
    All downloads are performed in background threads to prevent blocking.
    
    Usage:
        handler = AudioHandler()
        handler.on_playback_start = lambda item: print(f"Playing: {item.station_name}")
        handler.on_playback_complete = lambda item: print(f"Done: {item.message}")
        
        # Queue audio from comm history
        handler.queue_atc_audio(
            url="https://siaudio.s3.../audio.mp3",
            station_name="Truckee Tower",
            frequency="120.575",
            message="Roger, radar services terminated..."
        )
    """
    
    def __init__(self, 
                 cache_dir: Optional[str] = None,
                 player_config: Optional[AudioPlayerConfig] = None,
                 max_download_workers: int = 2):
        """
        Initialize the audio handler.
        
        Args:
            cache_dir: Custom cache directory for downloaded audio
            player_config: Custom player configuration
            max_download_workers: Max concurrent download threads
        """
        self.downloader = AudioDownloader(cache_dir=cache_dir)
        self.player = AudioPlayer(config=player_config)
        
        # Thread pool for async downloads
        self._download_executor = ThreadPoolExecutor(
            max_workers=max_download_workers,
            thread_name_prefix="AudioDownload"
        )
        
        # Track items currently in processing
        self._pending_items: List[AudioQueueItem] = []
        self._lock = threading.Lock()
        
        # Callbacks
        self.on_download_start: Optional[Callable[[AudioQueueItem], None]] = None
        self.on_download_complete: Optional[Callable[[AudioQueueItem, DownloadResult], None]] = None
        self.on_download_error: Optional[Callable[[AudioQueueItem, str], None]] = None
        self.on_playback_start: Optional[Callable[[AudioQueueItem], None]] = None
        self.on_playback_complete: Optional[Callable[[AudioQueueItem], None]] = None
        self.on_state_change: Optional[Callable[[PlayerState], None]] = None
        
        # Wire up player callbacks
        self.player.set_state_callback(self._on_player_state_change)
        self.player.set_error_callback(self._on_player_error)
        
        logger.info("AudioHandler initialized")
    
    def queue_atc_audio(self, 
                        url: str, 
                        station_name: str = "",
                        frequency: str = "",
                        message: str = "") -> bool:
        """
        Queue an ATC audio response for playback.
        
        Downloads the audio file asynchronously and queues it for playback.
        This method returns immediately - the download happens in background.
        
        Args:
            url: URL to the audio file (usually from atc_url in comm history)
            station_name: Name of the ATC station (e.g., "Truckee Tower")
            frequency: Radio frequency (e.g., "120.575")
            message: Text of the ATC message
            
        Returns:
            True if download was queued (doesn't mean it succeeded)
        """
        if not url:
            logger.warning("Empty audio URL, skipping")
            return False
        
        item = AudioQueueItem(
            url=url,
            station_name=station_name,
            frequency=frequency,
            message=message
        )
        
        # Notify download start
        if self.on_download_start:
            try:
                self.on_download_start(item)
            except Exception as e:
                logger.error(f"on_download_start callback error: {e}")
        
        # Submit download to thread pool - returns immediately
        self._download_executor.submit(self._download_and_queue, item)
        
        return True
    
    def _download_and_queue(self, item: AudioQueueItem):
        """
        Download audio and queue for playback.
        
        This runs in a background thread from the ThreadPoolExecutor.
        """
        try:
            # Download the file (this is the blocking call, but it's in a thread)
            result = self.downloader.download(item.url)
            item.download_result = result
            
            if result.success:
                # Notify download complete (might be called from thread)
                if self.on_download_complete:
                    try:
                        self.on_download_complete(item, result)
                    except Exception as e:
                        logger.error(f"on_download_complete callback error: {e}")
                
                # Queue for playback
                with self._lock:
                    self._pending_items.append(item)
                
                success = self.player.queue_file(
                    file_path=result.file_path,
                    on_start=lambda i=item: self._notify_playback_start(i),
                    on_complete=lambda i=item: self._notify_playback_complete(i),
                    metadata={
                        'station': item.station_name,
                        'frequency': item.frequency,
                        'message': item.message,
                        'url': item.url
                    }
                )
                
                if success:
                    logger.info(f"Queued ATC audio: {item.station_name} @ {item.frequency}")
            else:
                error = result.error or "Unknown download error"
                logger.error(f"Failed to download audio: {error}")
                if self.on_download_error:
                    try:
                        self.on_download_error(item, error)
                    except Exception as e:
                        logger.error(f"on_download_error callback error: {e}")
                        
        except Exception as e:
            logger.error(f"Error in download thread: {e}")
            if self.on_download_error:
                try:
                    self.on_download_error(item, str(e))
                except:
                    pass
    
    def _notify_playback_start(self, item: AudioQueueItem):
        """Internal callback when playback starts."""
        logger.debug(f"Playback started: {item.station_name}")
        if self.on_playback_start:
            try:
                self.on_playback_start(item)
            except Exception as e:
                logger.error(f"on_playback_start callback error: {e}")
    
    def _notify_playback_complete(self, item: AudioQueueItem):
        """Internal callback when playback completes."""
        logger.debug(f"Playback complete: {item.station_name}")
        
        # Remove from pending list
        with self._lock:
            if item in self._pending_items:
                self._pending_items.remove(item)
        
        if self.on_playback_complete:
            try:
                self.on_playback_complete(item)
            except Exception as e:
                logger.error(f"on_playback_complete callback error: {e}")
    
    def _on_player_state_change(self, state: PlayerState):
        """Internal handler for player state changes."""
        if self.on_state_change:
            try:
                self.on_state_change(state)
            except Exception as e:
                logger.error(f"on_state_change callback error: {e}")
    
    def _on_player_error(self, error: str):
        """Internal handler for player errors."""
        logger.error(f"Player error: {error}")
    
    # =========================================================================
    # Playback control passthrough
    # =========================================================================
    
    def play(self):
        """Resume playback if paused."""
        self.player.play()
    
    def pause(self):
        """Pause current playback."""
        self.player.pause()
    
    def stop(self):
        """Stop playback and clear queue."""
        self.player.stop()
        with self._lock:
            self._pending_items.clear()
    
    def skip(self):
        """Skip current audio."""
        self.player.skip()
    
    def set_volume(self, volume: float):
        """Set playback volume (0.0 to 1.0)."""
        self.player.set_volume(volume)
    
    def get_volume(self) -> float:
        """Get current volume level."""
        return self.player.get_volume()
    
    @property
    def state(self) -> PlayerState:
        """Get current player state."""
        return self.player.state
    
    @property
    def queue_size(self) -> int:
        """Get number of items queued for playback."""
        return self.player.queue_size()
    
    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self.player.state == PlayerState.PLAYING
    
    # =========================================================================
    # Cache management
    # =========================================================================
    
    def get_cache_stats(self):
        """Get audio cache statistics."""
        return self.downloader.get_cache_stats()
    
    def clear_cache(self):
        """Clear the audio cache."""
        return self.downloader.clear_cache()
    
    def shutdown(self):
        """Clean shutdown of the audio handler."""
        logger.info("Shutting down AudioHandler")
        self.player.stop()
        
        # Shutdown the download thread pool
        self._download_executor.shutdown(wait=False)
