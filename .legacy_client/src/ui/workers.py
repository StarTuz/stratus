"""
Worker threads for background operations.

Provides QThread-based workers for ATC calls to prevent UI freezing.
"""

from PySide6.QtCore import QObject, QThread, Signal, Slot
from typing import Optional, Callable, Any
import logging
import traceback

logger = logging.getLogger(__name__)


class SapiWorker(QObject):
    """
    Worker for executing ATC calls in a background thread.
    
    Usage:
        worker = SapiWorker(sapi.get_comms_history)
        worker.finished.connect(on_result)
        worker.error.connect(on_error)
        worker.start()
    """
    
    finished = Signal(object)  # Emits the result
    error = Signal(str)  # Emits error message
    started = Signal()
    
    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._thread: Optional[QThread] = None
    
    def start(self):
        """Start the worker in a new thread."""
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._run)
        self._thread.start()
        self.started.emit()
    
    @Slot()
    def _run(self):
        """Execute the function and emit results."""
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            logger.error(f"Worker error: {e}\n{traceback.format_exc()}")
            self.error.emit(str(e))
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Clean up the thread."""
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread.deleteLater()
            self._thread = None


class ConnectionWorker(QObject):
    """Worker specifically for ATC connection."""
    
    connected = Signal(bool, str)  # success, message
    finished = Signal()
    
    def __init__(self, sapi_factory: Callable):
        super().__init__()
        self.sapi_factory = sapi_factory
        self.sapi = None
        self._thread: Optional[QThread] = None
    
    def start(self):
        """Start connection in background thread."""
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._run)
        self._thread.start()
    
    @Slot()
    def _run(self):
        """Attempt connection."""
        try:
            self.sapi = self.sapi_factory()
            if self.sapi.connect():
                self.connected.emit(True, "Connected")
            else:
                self.connected.emit(False, "Connection failed")
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.connected.emit(False, str(e))
        finally:
            self.finished.emit()
            self._cleanup()
    
    def _cleanup(self):
        """Clean up the thread."""
        if self._thread:
            self._thread.quit()
            self._thread.wait()


class PollingWorker(QObject):
    """
    Worker for polling ATC in background.
    
    Unlike the simple workers, this one runs continuously.
    """
    
    data_received = Signal(list)  # List of CommEntry
    error = Signal(str)
    
    def __init__(self, sapi, interval_ms: int = 2000):
        super().__init__()
        self.sapi = sapi
        self.interval_ms = interval_ms
        self._running = False
        self._thread: Optional[QThread] = None
    
    def start(self):
        """Start polling."""
        if self._running:
            return
        
        self._running = True
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._run)
        self._thread.start()
    
    def stop(self):
        """Stop polling."""
        self._running = False
        if self._thread:
            self._thread.quit()
            self._thread.wait(3000)
    
    @Slot()
    def _run(self):
        """Polling loop."""
        import time
        
        while self._running:
            try:
                if self.sapi and self.sapi.is_connected:
                    response = self.sapi.get_comms_history()
                    if response.success and response.data:
                        self.data_received.emit(response.data)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                self.error.emit(str(e))
            
            # Sleep in small increments to allow quick shutdown
            for _ in range(int(self.interval_ms / 100)):
                if not self._running:
                    break
                time.sleep(0.1)


class SimpleWorker(QThread):
    """
    Simple worker thread that runs a function once.
    
    Usage:
        worker = SimpleWorker(my_function, arg1, arg2)
        worker.result.connect(handle_result)
        worker.start()
    """
    
    result = Signal(object)
    error = Signal(str)
    
    def __init__(self, func: Callable, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
    
    def run(self):
        """Execute the function."""
        try:
            result = self.func(*self.args, **self.kwargs)
            self.result.emit(result)
        except Exception as e:
            logger.error(f"Worker error: {e}")
            self.error.emit(str(e))
