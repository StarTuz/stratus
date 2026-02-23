"""
SECA Response Logger

STRATUS-004: Log all LLM responses for Self-Evolving Capability Audit.

Stores:
- Timestamp
- Prompt hash (for privacy)
- Full response
- Validation result
- Latency data

Log file: ~/.local/share/StratusATC/atc_responses.jsonl
"""

import json
import logging
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

DATA_DIR = Path.home() / ".local" / "share" / "StratusATC"
LOG_FILE = DATA_DIR / "atc_responses.jsonl"
MAX_LOG_SIZE_MB = 100


@dataclass
class SECALogEntry:
    """Single entry in the SECA audit log."""
    timestamp: str
    prompt_hash: str            # SHA256 of prompt (privacy-preserving)
    response: str               # Full LLM response
    response_length: int
    validation_valid: bool
    validation_issues: list
    latency_ms: Optional[float] = None
    model_id: str = "unknown"
    session_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SECALogger:
    """
    Self-Evolving Capability Audit Logger.
    
    Logs all LLM interactions for post-hoc analysis and behavioral drift detection.
    """
    
    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self._log_file = LOG_FILE
        self._entry_count = 0
        
        # Ensure directory exists
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Check for rotation
        self._check_rotation()
    
    def _check_rotation(self):
        """Rotate log if it exceeds max size."""
        if self._log_file.exists():
            size_mb = self._log_file.stat().st_size / (1024 * 1024)
            if size_mb > MAX_LOG_SIZE_MB:
                # Rotate: rename to .old and start fresh
                old_file = self._log_file.with_suffix(".jsonl.old")
                if old_file.exists():
                    old_file.unlink()
                self._log_file.rename(old_file)
                logger.info(f"[SECA] Rotated log file (was {size_mb:.1f}MB)")
    
    def log_response(
        self,
        prompt: str,
        response: str,
        validation_valid: bool,
        validation_issues: list,
        latency_ms: Optional[float] = None,
        model_id: str = "unknown",
        session_id: str = ""
    ):
        """
        Log an LLM response for SECA analysis.
        
        Args:
            prompt: The full prompt sent to LLM (will be hashed)
            response: The raw response from LLM
            validation_valid: Whether the response passed validation
            validation_issues: List of validation issues found
            latency_ms: End-to-end latency if available
            model_id: Ollama model identifier
            session_id: Latency tracking session ID
        """
        if not self._enabled:
            return
        
        entry = SECALogEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            prompt_hash=self._hash_prompt(prompt),
            response=response,
            response_length=len(response),
            validation_valid=validation_valid,
            validation_issues=validation_issues,
            latency_ms=latency_ms,
            model_id=model_id,
            session_id=session_id
        )
        
        try:
            with open(self._log_file, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
            self._entry_count += 1
            
            # Periodic rotation check
            if self._entry_count % 100 == 0:
                self._check_rotation()
                
        except Exception as e:
            logger.error(f"[SECA] Failed to write log: {e}")
    
    def _hash_prompt(self, prompt: str) -> str:
        """Hash prompt for privacy-preserving logging."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics from the log file for analysis."""
        if not self._log_file.exists():
            return {"entries": 0, "message": "No log file found"}
        
        try:
            entries = []
            with open(self._log_file, "r") as f:
                for line in f:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            
            if not entries:
                return {"entries": 0, "message": "No entries in log"}
            
            valid_count = sum(1 for e in entries if e.get("validation_valid", True))
            latencies = [e["latency_ms"] for e in entries if e.get("latency_ms")]
            
            return {
                "entries": len(entries),
                "valid_responses": valid_count,
                "invalid_responses": len(entries) - valid_count,
                "validation_rate": valid_count / len(entries) if entries else 0,
                "avg_latency_ms": sum(latencies) / len(latencies) if latencies else None,
                "max_latency_ms": max(latencies) if latencies else None,
                "min_latency_ms": min(latencies) if latencies else None,
                "log_file": str(self._log_file),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def enable(self):
        """Enable SECA logging."""
        self._enabled = True
        logger.info("[SECA] Logging enabled")
    
    def disable(self):
        """Disable SECA logging (for privacy)."""
        self._enabled = False
        logger.info("[SECA] Logging disabled")
    
    @property
    def is_enabled(self) -> bool:
        return self._enabled


# Global SECA logger instance
_seca_logger: Optional[SECALogger] = None


def get_seca_logger() -> SECALogger:
    """Get the global SECA logger instance."""
    global _seca_logger
    if _seca_logger is None:
        _seca_logger = SECALogger()
    return _seca_logger
