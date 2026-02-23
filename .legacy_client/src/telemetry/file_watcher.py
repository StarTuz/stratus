import json
import time
import os
import logging
from typing import Dict, Optional, Callable
from threading import Thread, Event

class StratusTelemetryWatcher:
    """
    Watches the stratus_telemetry.json file for updates from the X-Plane plugin.
    Also handles writing to stratus_commands.jsonl.
    """
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.input_file = os.path.join(data_dir, "stratus_telemetry.json")
        self.output_file = os.path.join(data_dir, "stratus_commands.jsonl")
        self.running = False
        self._thread: Optional[Thread] = None
        self._stop_event = Event()
        self.last_mtime = 0
        self.latest_data: Dict = {}
        self.on_data_update: Optional[Callable[[Dict], None]] = None
        self.logger = logging.getLogger("StratusTelemetryWatcher")

    def start(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        # Create dummy input file if it doesn't exist (for testing)
        if not os.path.exists(self.input_file):
            with open(self.input_file, 'w') as f:
                json.dump({"status": "waiting_for_sim", "timestamp": time.time()}, f)

        self.running = True
        self._stop_event.clear()
        self._thread = Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        self.logger.info(f"Started watching {self.input_file}")

    def stop(self):
        self.running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join()

    def _watch_loop(self):
        while self.running:
            try:
                if os.path.exists(self.input_file):
                    mtime = os.path.getmtime(self.input_file)
                    if mtime > self.last_mtime:
                        self.last_mtime = mtime
                        self._read_input()
            except Exception as e:
                self.logger.error(f"Error checking file: {e}")
            
            time.sleep(0.5) # Check every 500ms

    def _read_input(self):
        try:
            with open(self.input_file, 'r') as f:
                data = json.load(f)
                self.latest_data = data
                if self.on_data_update:
                    self.on_data_update(data)
                self.logger.debug("Stratus telemetry updated")
        except json.JSONDecodeError:
            self.logger.warning("Failed to decode JSON from input file (sim writing?)")
        except Exception as e:
            self.logger.error(f"Error reading input: {e}")

    def send_command(self, command: Dict):
        """Append a command to the output JSONL file"""
        try:
            with open(self.output_file, 'a') as f:
                f.write(json.dumps(command) + "\n")
        except Exception as e:
            self.logger.error(f"Error writing output: {e}")
