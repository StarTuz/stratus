"""
Latency Measurement Module for Stratus ATC

STRATUS-001: Measures end-to-end latency of the PTT → Audio pipeline.

Usage:
    from core.latency import LatencyTracker
    
    tracker = LatencyTracker()
    tracker.start("ptt")              # When PTT pressed
    tracker.mark("stt_complete")      # When STT finishes
    tracker.mark("llm_complete")      # When LLM responds
    tracker.mark("tts_complete")      # When TTS finishes
    tracker.end()                     # Finalize measurement
    
    report = tracker.get_report()     # Get timing breakdown
"""

import time
import logging
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

DATA_DIR = Path.home() / ".local" / "share" / "StratusATC"


@dataclass
class LatencyMeasurement:
    """Single latency measurement for a transmission."""
    session_id: str
    start_time: float
    marks: Dict[str, float] = field(default_factory=dict)
    end_time: Optional[float] = None
    
    @property
    def total_ms(self) -> Optional[float]:
        """Total end-to-end latency in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000
    
    def get_segment_ms(self, start_mark: str, end_mark: str) -> Optional[float]:
        """Get latency between two marks in milliseconds."""
        if start_mark not in self.marks or end_mark not in self.marks:
            return None
        return (self.marks[end_mark] - self.marks[start_mark]) * 1000
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        result = {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "marks": self.marks,
            "end_time": self.end_time,
            "total_ms": self.total_ms,
        }
        # Calculate segment timings
        if self.marks:
            segments = {}
            prev_time = self.start_time
            prev_name = "start"
            for mark_name, mark_time in sorted(self.marks.items(), key=lambda x: x[1]):
                segment_name = f"{prev_name}_to_{mark_name}"
                segments[segment_name] = (mark_time - prev_time) * 1000
                prev_time = mark_time
                prev_name = mark_name
            if self.end_time:
                segments[f"{prev_name}_to_end"] = (self.end_time - prev_time) * 1000
            result["segments_ms"] = segments
        return result


class LatencyTracker:
    """
    Track latency through the PTT → Audio pipeline.
    
    Pipeline stages:
    1. PTT pressed (start)
    2. STT complete (stt_complete)
    3. LLM response (llm_complete) 
    4. TTS finished (tts_complete)
    5. Audio played (end)
    """
    
    def __init__(self, log_to_file: bool = True):
        self._current: Optional[LatencyMeasurement] = None
        self._history: List[LatencyMeasurement] = []
        self._log_to_file = log_to_file
        self._session_counter = 0
        self._log_file = DATA_DIR / "latency.jsonl"
        
        # Ensure data directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    def start(self, label: str = "ptt") -> str:
        """Start a new latency measurement. Returns session ID."""
        self._session_counter += 1
        session_id = f"{label}_{int(time.time())}_{self._session_counter}"
        
        self._current = LatencyMeasurement(
            session_id=session_id,
            start_time=time.time()
        )
        
        logger.debug(f"[LATENCY] Started measurement: {session_id}")
        return session_id
    
    def mark(self, name: str) -> Optional[float]:
        """
        Add a timing mark. Returns milliseconds since start.
        
        Common marks:
        - stt_complete: STT transcription finished
        - llm_start: Before calling LLM
        - llm_complete: LLM response received
        - tts_start: Before calling TTS
        - tts_complete: TTS audio generated
        """
        if self._current is None:
            logger.warning(f"[LATENCY] Mark '{name}' called with no active measurement")
            return None
        
        mark_time = time.time()
        self._current.marks[name] = mark_time
        ms_since_start = (mark_time - self._current.start_time) * 1000
        
        logger.debug(f"[LATENCY] Mark '{name}': {ms_since_start:.1f}ms since start")
        return ms_since_start
    
    def end(self) -> Optional[LatencyMeasurement]:
        """End the current measurement and log it."""
        if self._current is None:
            logger.warning("[LATENCY] end() called with no active measurement")
            return None
        
        self._current.end_time = time.time()
        measurement = self._current
        self._current = None
        
        # Add to history
        self._history.append(measurement)
        
        # Log to file
        if self._log_to_file:
            self._write_to_file(measurement)
        
        # Log summary
        total = measurement.total_ms
        logger.info(f"[LATENCY] Completed {measurement.session_id}: {total:.1f}ms total")
        
        # Log segment breakdown
        if measurement.marks:
            segments = measurement.to_dict().get("segments_ms", {})
            for seg_name, seg_ms in segments.items():
                logger.info(f"[LATENCY]   {seg_name}: {seg_ms:.1f}ms")
        
        return measurement
    
    def abort(self):
        """Abort current measurement without logging."""
        if self._current:
            logger.debug(f"[LATENCY] Aborted {self._current.session_id}")
        self._current = None
    
    def _write_to_file(self, measurement: LatencyMeasurement):
        """Append measurement to JSONL log file."""
        try:
            with open(self._log_file, "a") as f:
                data = measurement.to_dict()
                data["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            logger.error(f"[LATENCY] Failed to write log: {e}")
    
    def get_report(self) -> Dict:
        """Get a summary report of all measurements."""
        if not self._history:
            return {"count": 0, "message": "No measurements recorded"}
        
        totals = [m.total_ms for m in self._history if m.total_ms is not None]
        
        if not totals:
            return {"count": len(self._history), "message": "No completed measurements"}
        
        return {
            "count": len(totals),
            "min_ms": min(totals),
            "max_ms": max(totals),
            "avg_ms": sum(totals) / len(totals),
            "target_ms": 2000,  # 2 second target
            "under_target": sum(1 for t in totals if t < 2000),
            "over_target": sum(1 for t in totals if t >= 2000),
        }
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get recent measurements as dictionaries."""
        return [m.to_dict() for m in self._history[-limit:]]


# Global tracker instance
_tracker: Optional[LatencyTracker] = None


def get_tracker() -> LatencyTracker:
    """Get the global latency tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = LatencyTracker()
    return _tracker
