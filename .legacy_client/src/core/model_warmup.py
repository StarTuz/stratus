"""
Model Warmup Service for Stratus ATC

Keeps the Ollama model hot by sending periodic lightweight prompts.
This eliminates cold-start latency (5-15s) when the model hasn't been
used recently.

The daemon sends a heartbeat every 30 seconds during idle periods.
It automatically pauses when PTT is active to avoid competing for GPU.
"""

import logging
import threading
import time
import requests
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Default Ollama endpoint
OLLAMA_URL = "http://localhost:11434/api/generate"

# Minimal warmup prompt that keeps model in memory but generates minimal output
WARMUP_PROMPT = "Ready"
WARMUP_EXPECTED = "Standing by"  # We don't check this, just keep model hot


class ModelWarmupService:
    """
    Keeps Ollama model loaded in GPU memory by sending periodic heartbeats.
    
    Cold-start times for Ollama can be 5-15 seconds when the model needs
    to be loaded into GPU memory. This service prevents that by sending
    a minimal prompt every 30 seconds during idle periods.
    """
    
    def __init__(
        self,
        model: str = "llama3.2:3b",
        interval_seconds: float = 30.0,
        ollama_url: str = OLLAMA_URL,
    ):
        """
        Initialize warmup service.
        
        Args:
            model: Ollama model name to keep warm
            interval_seconds: Seconds between heartbeats (default: 30)
            ollama_url: Ollama API endpoint
        """
        self.model = model
        self.interval_seconds = interval_seconds
        self.ollama_url = ollama_url
        
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Stats
        self.last_heartbeat: Optional[float] = None
        self.heartbeat_count = 0
        self.last_latency_ms: float = 0.0
        
        # Callbacks
        self.on_heartbeat: Optional[Callable[[float], None]] = None
        self.on_cold_start: Optional[Callable[[float], None]] = None
        
        logger.info(f"ModelWarmupService initialized: model={model}, interval={interval_seconds}s")
    
    def start(self):
        """Start the warmup service."""
        if self._running:
            logger.warning("Warmup service already running")
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._warmup_loop, daemon=True)
        self._thread.start()
        logger.info("Warmup service started")
    
    def stop(self):
        """Stop the warmup service."""
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Warmup service stopped")
    
    def pause(self):
        """Pause heartbeats (e.g., when PTT is active)."""
        self._paused = True
        logger.debug("Warmup service paused")
    
    def resume(self):
        """Resume heartbeats."""
        self._paused = False
        logger.debug("Warmup service resumed")
    
    def _warmup_loop(self):
        """Main heartbeat loop."""
        while self._running:
            # Wait for interval (but check stop event frequently)
            for _ in range(int(self.interval_seconds * 10)):
                if self._stop_event.is_set():
                    return
                time.sleep(0.1)
            
            # Skip if paused
            if self._paused:
                continue
            
            # Send heartbeat
            try:
                latency = self._send_heartbeat()
                if latency is not None:
                    self.last_heartbeat = time.time()
                    self.last_latency_ms = latency
                    self.heartbeat_count += 1
                    
                    # Check for cold start (>2s is slow)
                    if latency > 2000 and self.on_cold_start:
                        self.on_cold_start(latency)
                    elif self.on_heartbeat:
                        self.on_heartbeat(latency)
                    
                    logger.debug(f"Warmup heartbeat: {latency:.0f}ms")
                    
            except Exception as e:
                logger.warning(f"Warmup heartbeat failed: {e}")
    
    def _send_heartbeat(self) -> Optional[float]:
        """
        Send a minimal prompt to keep model warm.
        
        Returns:
            Latency in milliseconds, or None if failed
        """
        start = time.time()
        
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": WARMUP_PROMPT,
                    "stream": False,
                    # Minimal generation
                    "options": {
                        "num_predict": 5,  # Only generate a few tokens
                        "temperature": 0.0,  # Deterministic
                    }
                },
                timeout=15.0,
            )
            response.raise_for_status()
            
            latency_ms = (time.time() - start) * 1000
            return latency_ms
            
        except requests.exceptions.ConnectionError:
            logger.debug("Ollama not running, skipping warmup")
            return None
        except requests.exceptions.Timeout:
            logger.warning("Warmup timed out (model might need initial load)")
            return None
        except Exception as e:
            logger.warning(f"Warmup error: {e}")
            return None
    
    def force_warmup(self) -> float:
        """
        Force an immediate warmup and return latency.
        
        Useful for pre-warming before expected use.
        
        Returns:
            Latency in milliseconds
        """
        logger.info("Forcing model warmup...")
        latency = self._send_heartbeat()
        if latency:
            logger.info(f"Model warmed up in {latency:.0f}ms")
            return latency
        return 0.0
    
    def get_status(self) -> dict:
        """Get current warmup service status."""
        return {
            "running": self._running,
            "paused": self._paused,
            "model": self.model,
            "interval_seconds": self.interval_seconds,
            "heartbeat_count": self.heartbeat_count,
            "last_heartbeat": self.last_heartbeat,
            "last_latency_ms": self.last_latency_ms,
        }
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def is_paused(self) -> bool:
        return self._paused


# Global singleton for easy access
_warmup_service: Optional[ModelWarmupService] = None


def get_warmup_service() -> ModelWarmupService:
    """Get the global warmup service singleton."""
    global _warmup_service
    if _warmup_service is None:
        _warmup_service = ModelWarmupService()
    return _warmup_service


def start_warmup(model: str = "llama3.2:3b", interval: float = 30.0):
    """Convenience function to start warmup service."""
    service = get_warmup_service()
    service.model = model
    service.interval_seconds = interval
    service.start()
    return service


def stop_warmup():
    """Convenience function to stop warmup service."""
    global _warmup_service
    if _warmup_service:
        _warmup_service.stop()


# Test runner
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("Testing Model Warmup Service")
    print("=" * 40)
    
    service = ModelWarmupService(interval_seconds=5.0)
    
    def on_heartbeat(latency: float):
        print(f"  ❤️  Heartbeat: {latency:.0f}ms")
    
    def on_cold_start(latency: float):
        print(f"  🥶 Cold start detected: {latency:.0f}ms")
    
    service.on_heartbeat = on_heartbeat
    service.on_cold_start = on_cold_start
    
    # Force initial warmup
    print("\nForcing initial warmup...")
    initial = service.force_warmup()
    print(f"Initial warmup: {initial:.0f}ms")
    
    # Start service
    print("\nStarting warmup service (5s interval for testing)...")
    service.start()
    
    try:
        # Let it run for 30 seconds
        time.sleep(30)
    except KeyboardInterrupt:
        pass
    
    service.stop()
    print(f"\nTotal heartbeats: {service.heartbeat_count}")
