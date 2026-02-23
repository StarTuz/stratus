"""
Stratus Main Window

The primary GUI window for the native Linux client.
Uses background threads for all ATC network calls to prevent UI freezing.
Includes ComLink web server for tablet/phone access.
"""

import sys
import os
import logging
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QStatusBar, QLabel, QApplication, QMessageBox,
    QSystemTrayIcon, QScrollArea, QToolButton
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread, QSettings
from PySide6.QtGui import QAction, QIcon, QCloseEvent

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .styles import get_stylesheet, get_color
from .comms_widget import CommsHistoryWidget
from .frequency_panel import FrequencyPanel
from .transmission_panel import TransmissionPanel
from core.copilot import CoPilot
from .status_panel import StatusPanel
from .settings_panel import SettingsPanel
from .workers import SimpleWorker
from .system_tray import SystemTray

from core.providers.factory import get_provider, IATCProvider
from core.sapi_interface import CommEntry, Channel
from core.sim_data import SimDataInterface
from core.speech_interface import SpeechInterface
from core.airport_manager import AirportManager
from core.latency import get_tracker as get_latency_tracker
from core.validation import validate_atc_response, get_fallback_response, sanitize_for_tts
from core.seca_logger import get_seca_logger
from core.flight_phase import get_flight_phase_tracker, FlightPhase
from core.atc_prompt import build_atc_prompt
from audio import AudioHandler, PlayerState

# Optional: ComLink web server (may not be available if flask not installed)
try:
    from web import ComLinkServer
    HAS_COMLINK = True
except ImportError:
    HAS_COMLINK = False
    ComLinkServer = None

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for Stratus client."""
    
    # Signals for thread-safe UI updates
    comms_updated = Signal(list)  # List of CommEntry
    connection_changed = Signal(bool, str)  # connected, status_message
    audio_state_changed = Signal(str, str)  # state, info
    status_message = Signal(str)  # For thread-safe status bar updates
    
    def __init__(self, parent=None, enable_web: bool = True, web_port: int = 8080):
        super().__init__(parent)
        
        # State
        self.sapi: Optional[IATCProvider] = None
        self.audio: Optional[AudioHandler] = None
        self._polling = False
        self._poll_timer: Optional[QTimer] = None
        self._played_comm_ids: set = set()
        self._active_workers: List[SimpleWorker] = []  # Keep references to prevent GC
        self._minimize_to_tray = True  # Minimize to tray instead of closing
        
        # ATC conversation history for context
        self._atc_history: List[str] = []  # Last N pilot/ATC exchanges
        
        # Airport Database
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        airports_csv = os.path.join(base_dir, "core", "resources", "airports.csv")
        runways_csv = os.path.join(base_dir, "core", "resources", "runways.csv")
        self.airports = AirportManager(airports_csv, runways_csv)

        
        # Flight State
        self._last_phase = "UNKNOWN"
        self._last_alt = 0
        
        # ComLink web server
        self._enable_web = enable_web and HAS_COMLINK
        self._web_port = web_port
        self.comlink: Optional[ComLinkServer] = None
        self._cached_comms: List[Dict[str, Any]] = []  # For ComLink sync
        
        # Copilot
        self.copilot = None
        
        # Identity Overrides (Phase 24)
        self._identity_overrides = {
            "callsign": "",
            "type": ""
        }
        
        # Initialize
        self._setup_window()
        self._setup_menu()
        self._setup_ui()
        self._setup_tray()
        self._setup_comlink()
        self._connect_signals()
        self._init_services()
        
        self._init_services()
        self._load_settings()  # Load persistent settings
        
        logger.info("Main window initialized")
    
    def _setup_window(self):
        """Configure the main window."""
        self.setWindowTitle("StratusATC - Native Mac/Linux Client")
        self.resize(1400, 850)
        self.setMinimumSize(1100, 700)
        
        # Apply stylesheet
        self.setStyleSheet(get_stylesheet())
        
        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def _setup_menu(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        connect_action = QAction("&Connect", self)
        connect_action.setShortcut("Ctrl+Shift+C")
        connect_action.triggered.connect(self._on_connect)
        file_menu.addAction(connect_action)
        
        disconnect_action = QAction("&Disconnect", self)
        disconnect_action.triggered.connect(self._on_disconnect)
        file_menu.addAction(disconnect_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        refresh_action = QAction("&Refresh History", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_history)
        view_menu.addAction(refresh_action)
        
        clear_action = QAction("&Clear History", self)
        clear_action.triggered.connect(lambda: self.comms_widget.clear_history())
        view_menu.addAction(clear_action)
        
        reset_action = QAction("&Reset Session", self)
        reset_action.setToolTip("Force a session state refresh to resolve location issues")
        reset_action.triggered.connect(self._reset_sapi_session)
        view_menu.addAction(reset_action)

        
        view_menu.addSeparator()
        
        # Always on top toggle
        self.always_on_top_action = QAction("Always on &Top", self)
        self.always_on_top_action.setCheckable(True)
        self.always_on_top_action.triggered.connect(self._toggle_always_on_top)
        view_menu.addAction(self.always_on_top_action)
        
        # Compact mode for overlay
        self.compact_action = QAction("&Compact Mode", self)
        self.compact_action.setCheckable(True)
        self.compact_action.triggered.connect(self._toggle_compact_mode)
        view_menu.addAction(self.compact_action)
        
        # Audio menu
        audio_menu = menubar.addMenu("&Audio")
        
        play_all_action = QAction("&Play All New", self)
        play_all_action.setShortcut("Ctrl+P")
        play_all_action.triggered.connect(self._play_all_audio)
        audio_menu.addAction(play_all_action)
        
        stop_action = QAction("&Stop Playback", self)
        stop_action.setShortcut("Escape")
        stop_action.triggered.connect(self._stop_audio)
        audio_menu.addAction(stop_action)
        
        # Polling submenu
        audio_menu.addSeparator()
        
        self.poll_action = QAction("Enable &Polling", self)
        self.poll_action.setCheckable(True)
        self.poll_action.triggered.connect(self._toggle_polling)
        audio_menu.addAction(self.poll_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_ui(self):
        """Create the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Status panel at top
        self.status_panel = StatusPanel()
        self.status_panel.setStyleSheet(f"background-color: {get_color('bg_secondary')};")
        main_layout.addWidget(self.status_panel)
        
        # Main content area
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)
        
        # Left panel: Comms history (main area)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        
        self.comms_widget = CommsHistoryWidget()
        left_layout.addWidget(self.comms_widget, stretch=1)
        
        # Transmission panel
        self.transmission_panel = TransmissionPanel()
        left_layout.addWidget(self.transmission_panel)
        
        content_layout.addWidget(left_panel, stretch=2)
        
        # Right panel: Frequencies and settings (scrollable)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setFixedWidth(400)
        right_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        
        self.frequency_panel = FrequencyPanel()
        right_layout.addWidget(self.frequency_panel)
        
        # Settings panel
        self.settings_panel = SettingsPanel()
        right_layout.addWidget(self.settings_panel)
        
        right_layout.addStretch()
        
        right_scroll.setWidget(right_panel)
        content_layout.addWidget(right_scroll)
        
        main_layout.addWidget(content_widget, stretch=1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Connect to ATC to begin.")
    
    def _connect_signals(self):
        """Connect all signals to slots."""
        # Status panel
        self.status_panel.connect_clicked.connect(self._on_connect)
        self.status_panel.disconnect_clicked.connect(self._on_disconnect)
        self.status_panel.volume_changed.connect(self._on_volume_changed)
        
        # Transmission panel
        self.transmission_panel.send_transmission.connect(self._on_send_transmission)
        
        # Comms widget
        self.comms_widget.play_audio_requested.connect(self._on_play_audio)
        
        # Frequency panel
        self.frequency_panel.tune_frequency.connect(self._on_tune_frequency)
        self.frequency_panel.swap_frequency.connect(self._on_swap_frequency)
        
        # Settings panel
        self.settings_panel.session_reset_requested.connect(self._reset_sapi_session)
        
        # Thread-safe signals
        self.comms_updated.connect(self._handle_comms_update)

        self.connection_changed.connect(self._handle_connection_change)
        self.audio_state_changed.connect(self._handle_audio_state)
        self.status_message.connect(self.status_bar.showMessage)
        
        # System tray signals
        if self.tray.is_available:
            self.tray.show_window.connect(self._show_from_tray)
            self.tray.quit_app.connect(self._quit_app)
            self.tray.toggle_polling.connect(self._toggle_polling)
        
        # Settings panel signals
        self.settings_panel.atc_mode_changed.connect(self._on_atc_mode_changed)
        self.settings_panel.cabin_crew_toggled.connect(self._on_cabin_crew_toggled)
        self.settings_panel.tour_guide_toggled.connect(self._on_tour_guide_toggled)
        self.settings_panel.mentor_toggled.connect(self._on_mentor_toggled)
        self.settings_panel.brain_start_requested.connect(self._on_brain_start_requested)
        self.settings_panel.brain_start_requested.connect(self._on_brain_start_requested)
        self.settings_panel.brain_pull_requested.connect(self._on_brain_pull_requested)
        self.settings_panel.callsign_override_changed.connect(self._on_callsign_override_changed)
        self.settings_panel.aircraft_type_override_changed.connect(self._on_type_override_changed)

    
    def _setup_tray(self):
        """Initialize system tray."""
        self.tray = SystemTray(self)
        logger.info(f"System tray available: {self.tray.is_available}")
    
    def _setup_comlink(self):
        """Initialize ComLink web server for tablet/phone access."""
        if not self._enable_web:
            logger.info("ComLink web server disabled")
            return
        
        if not HAS_COMLINK:
            logger.warning("ComLink not available - install flask and flask-socketio")
            return
        
        try:
            self.comlink = ComLinkServer(port=self._web_port)
            
            # Wire up callbacks from web -> app
            self.comlink.on_send_transmission = self._comlink_send_transmission
            self.comlink.on_tune_frequency = self._comlink_tune_frequency
            self.comlink.on_tune_standby = self._comlink_tune_standby
            self.comlink.on_swap_frequency = self._comlink_swap_frequency
            self.comlink.on_play_audio = self._comlink_play_audio
            self.comlink.on_toggle_copilot = self._comlink_toggle_copilot
            self.comlink.on_brain_start = self._on_brain_start_requested
            self.comlink.on_brain_pull = self._on_brain_pull_requested
            
            # Start the server
            self.comlink.start()
            logger.info(f"ComLink web server started at http://localhost:{self._web_port}/comlink")
            
        except Exception as e:
            logger.error(f"Failed to start ComLink: {e}")
            self.comlink = None
    
    # ComLink callback handlers
    def _comlink_send_transmission(self, message: str, channel: str):
        """Handle transmission from ComLink web interface."""
        self._on_send_transmission(message, channel)
    
    def _comlink_tune_frequency(self, channel: str, frequency: str):
        """Handle frequency tune from ComLink."""
        self._on_tune_frequency(channel, frequency)
    
    def _comlink_tune_standby(self, channel: str, frequency: str):
        """Handle standby tune from ComLink."""
        # Set standby frequency via sim data
        if channel == "COM1":
            self.sim_data.set_com1_standby(frequency)
        else:
            self.sim_data.set_com2_standby(frequency)
        self.status_bar.showMessage(f"Set {channel} standby to {frequency}")
    
    def _comlink_swap_frequency(self, channel: str):
        """Handle frequency swap from ComLink."""
        self._on_swap_frequency(channel)
    
    def _comlink_play_audio(self, url: str):
        """Handle audio play request from ComLink."""
        if self.audio:
            self.audio.queue_atc_audio(url, "ATC", "", "")
    
    def _comlink_toggle_copilot(self, enabled: bool):
        """Handle copilot toggle from ComLink web interface."""
        if enabled:
            self.copilot.enable(CopilotMode.FULL)
            self.status_bar.showMessage("🤖 Copilot enabled from ComLink")
        else:
            self.copilot.disable()
            self.status_bar.showMessage("Copilot disabled from ComLink")
        # Sync the GUI button state
        self.transmission_panel.set_copilot_active(enabled)
    
    def _show_from_tray(self):
        """Show window from tray."""
        self.showNormal()
        self.activateWindow()
        self.raise_()
    
    def _quit_app(self):
        """Quit the application completely."""
        self._minimize_to_tray = False  # Allow actual close
        self.close()
    
    def _init_services(self):
        self._polling = False
        self._played_comm_ids = set()
        self._initial_load_complete = False
        
        # Audio handler
        self.audio = AudioHandler()
        self.audio.on_playback_start = self._on_audio_start
        self.audio.on_playback_complete = self._on_audio_complete
        self.audio.on_state_change = self._on_audio_state_change
        
        # Initialize sim data interface for X-Plane communication
        self.sim_data = SimDataInterface()
        
        # Start telemetry polling (every 500ms to update frequencies)
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.timeout.connect(self._update_telemetry)
        self._telemetry_timer.start(500)  # 500ms for responsiveness

        # Brain status monitoring (every 5 seconds)
        self._brain_timer = QTimer(self)
        self._brain_timer.timeout.connect(self._update_brain_status)
        self._brain_timer.start(5000)

        
        # Disable transmission until connected
        self.transmission_panel.set_enabled(False)
        
        # Initialize copilot callbacks
        self._init_copilot()
        
        # Initialize speech interface
        self.speech = SpeechInterface()
        self._init_speech()
    
    def _init_speech(self):
        """Initialize speech integration."""
        if self.speech.is_available:
            logger.info("Speech Interface available")
            if self.comlink:
                self.comlink.send_toast("Speech Service Connected", "success")
        else:
            logger.warning("Speech Interface not available")
            
        # Wire up PTT button from transmission panel
        self.transmission_panel.voice_input_requested.connect(self._on_start_ptt)
    
    @Slot()
    def _on_start_ptt(self):
        """Handle PTT start (Listen for Speech)."""
        if not self.speech.is_available:
            self.status_bar.showMessage("Error: Speech service not connected")
            return
        
        # STRATUS-001: Start latency measurement
        latency = get_latency_tracker()
        latency.start("ptt")
            
        self.status_bar.showMessage("Listening... Speak now")
        self.transmission_panel.set_transmitting_state(True)
        
        # PTT Countdown timer
        self._ptt_countdown = 5
        self._ptt_timer = QTimer(self)
        self._ptt_timer.timeout.connect(self._update_ptt_countdown)
        self._ptt_timer.start(1000)
        self.transmission_panel.ptt_btn.setText(f"TX ({self._ptt_countdown})")
        
        # Start background worker for STT
        self._stt_worker = self._run_in_background(
            self.speech.listen_vad, 
            self._on_stt_result, 
            self._on_stt_error
        )

    def _update_ptt_countdown(self):
        """Update the PTT button text with remaining time."""
        self._ptt_countdown -= 1
        if self._ptt_countdown <= 0:
            self._stop_ptt_timer()
        else:
            self.transmission_panel.ptt_btn.setText(f"TX ({self._ptt_countdown})")

    def _stop_ptt_timer(self):
        """Stop and clean up the PTT timer."""
        if hasattr(self, '_ptt_timer') and self._ptt_timer:
            self._ptt_timer.stop()
        self.transmission_panel.set_transmitting_state(False)
        
    def _on_stt_result(self, text):
        """Handle STT transcription result."""
        self._stop_ptt_timer()
        self._stt_worker = None
        
        # STRATUS-001: Mark STT complete
        latency = get_latency_tracker()
        latency.mark("stt_complete")
        
        # Process transcribed text
        if text:
            # Send the transcribed text
            channel = self.transmission_panel._current_channel
            logger.info(f"STT Heard: '{text}' sending on {channel}")
            self.status_bar.showMessage(f"Heard: '{text}'")
            self._on_send_transmission(text, channel)
        else:
            self.status_bar.showMessage("Listening timed out or no speech detected")
            latency.abort()  # No valid speech, abort measurement
            
    @Slot(str)
    def _on_stt_error(self, error):
        """Handle STT error."""
        self._stop_ptt_timer()
        self._stt_worker = None
        logger.error(f"STT Error: {error}")
        self.status_bar.showMessage(f"Voice Input Error: {error}")
    
    def _init_copilot(self):
        """Initialize copilot."""
        # Initialize the new AI Co-pilot action layer
        self.copilot = CoPilot(self.sim_data)
        
        # Connect transmission panel copilot toggle
        self.transmission_panel.copilot_toggled.connect(self._on_copilot_toggled)
        
        logger.info("Co-pilot initialized")
    
    
    @Slot(bool)
    def _on_copilot_toggled(self, enabled: bool):
        """Handle copilot toggle from UI."""
        if self.copilot:
            self.copilot.set_enabled(enabled)
            
            if enabled:
                self.status_bar.showMessage("🤖 AI Co-pilot enabled - Automation Active")
                if self.comlink:
                    self.comlink.send_toast("Co-pilot enabled", "success")
            else:
                self.status_bar.showMessage("AI Co-pilot disabled")
                if self.comlink:
                    self.comlink.send_toast("Co-pilot disabled", "info")
    
    def _run_in_background(self, func, on_result=None, on_error=None):
        """
        Run a function in a background thread.
        
        This is the key method for preventing UI freezing.
        """
        worker = SimpleWorker(func)
        
        if on_result:
            worker.result.connect(on_result)
        if on_error:
            worker.error.connect(on_error)
        
        # Clean up worker when done
        worker.finished.connect(lambda: self._cleanup_worker(worker))
        
        # Keep reference to prevent garbage collection
        self._active_workers.append(worker)
        
        worker.start()
        return worker
    
    def _cleanup_worker(self, worker):
        """Remove worker from active list."""
        if worker in self._active_workers:
            self._active_workers.remove(worker)
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    @Slot()
    def _on_connect(self):
        """Handle connect button - runs connection in background thread."""
        self.status_bar.showMessage("Connecting to ATC...")
        self.status_panel.set_connected(False, "Connecting...")
        
        def do_connect():
            """This runs in background thread."""
            sapi = get_provider()
            if sapi.connect():
                return sapi
            return None
        
        def on_connected(sapi):
            """This runs on UI thread via signal."""
            if sapi:
                self.sapi = sapi
                self.connection_changed.emit(True, "Connected")
                self.status_message.emit("Connected to Stratus API")
                self._refresh_history()
                self._start_polling()
            else:
                self.connection_changed.emit(False, "Connection failed")
                self.status_message.emit("Failed to connect to ATC")
                QMessageBox.warning(self, "Connection Failed", 
                    "Could not connect to ATC Provider.\nCheck configuration and ensure backend (Speech Daemon or SAPI) is reachable.")
        
        def on_error(error):
            """Handle connection error."""
            logger.error(f"Connection error: {error}")
            self.connection_changed.emit(False, f"Error: {error}")
            self.status_message.emit(f"Connection error: {error}")
        
        self._run_in_background(do_connect, on_connected, on_error)
    
    @Slot()
    def _on_disconnect(self):
        """Handle disconnect button."""
        self._stop_polling()
        self.sapi = None
        self._initial_load_complete = False  # Reset so we don't play old audio on reconnect
        self.connection_changed.emit(False, "Disconnected")
        self.status_bar.showMessage("Disconnected")
    
    @Slot(bool, str)
    def _handle_connection_change(self, connected: bool, status: str):
        """Update UI for connection state change."""
        self.status_panel.set_connected(connected, status)
        self.transmission_panel.set_enabled(connected)
        
        # Update tray icon
        if self.tray.is_available:
            self.tray.set_connected(connected, status)
        
        # Update ComLink
        if self.comlink:
            self.comlink.update_connection_status(connected, status)
    
    # =========================================================================
    # Polling
    # =========================================================================
    
    def _start_polling(self):
        """Start polling for new communications."""
        if self._polling:
            return
        
        self._polling = True
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_comms)
        self._poll_timer.start(5000)  # 5 second interval (increased for stability)
        
        self.poll_action.setChecked(True)
        self.status_panel.set_polling(True, 5.0)
        if self.tray.is_available:
            self.tray.set_polling(True)
        logger.info("Polling started")
    
    def _stop_polling(self):
        """Stop polling."""
        self._polling = False
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None
        
        self.poll_action.setChecked(False)
        self.status_panel.set_polling(False)
        if self.tray.is_available:
            self.tray.set_polling(False)
        logger.info("Polling stopped")
    
    @Slot()
    def _toggle_polling(self):
        """Toggle polling on/off."""
        if self._polling:
            self._stop_polling()
        else:
            if self.sapi and self.sapi.is_connected:
                self._start_polling()
    
    @Slot()
    def _poll_comms(self):
        """Poll for new communications - runs in background thread."""
        if not self.sapi or not self.sapi.is_connected:
            return
        
        def do_poll():
            """This runs in background thread."""
            telemetry = self.sim_data.read_telemetry()
            response = self.sapi.get_comms_history(
                lat=telemetry.latitude if telemetry else None,
                lon=telemetry.longitude if telemetry else None
            )
            if response.success and response.data:


                return response.data
            return None
        
        def on_result(data):
            """Handle poll result on UI thread."""
            if data:
                self.comms_updated.emit(data)
        
        self._run_in_background(do_poll, on_result)
    
    @Slot()
    def _refresh_history(self):
        """Manually refresh comms history - runs in background thread."""
        if not self.sapi or not self.sapi.is_connected:
            return
        
        self.status_bar.showMessage("Refreshing history...")
        
        def do_refresh():
            """This runs in background thread."""
            telemetry = self.sim_data.read_telemetry()
            response = self.sapi.get_comms_history(
                lat=telemetry.latitude if telemetry else None,
                lon=telemetry.longitude if telemetry else None
            )
            return response


        
        def on_result(response):
            """Handle result on UI thread."""
            if response.success and response.data:
                self.comms_updated.emit(response.data)
                self.status_message.emit(f"Loaded {len(response.data)} communications")
            else:
                self.status_message.emit(f"Failed to load history: {response.error}")
        
        def on_error(error):
            self.status_message.emit(f"Error: {error}")
        
        self._run_in_background(do_refresh, on_result, on_error)
    
    @Slot(list)
    def _handle_comms_update(self, entries: list):
        """Handle new comms data (runs on UI thread)."""
        self.comms_widget.update_from_entries(entries)
        
        # Write to overlay file
        try:
            overlay_msgs = []
            for entry in entries:
                overlay_msgs.append({
                    "station": entry.station_name,
                    "message": entry.outgoing_message,
                    "timestamp": time.time(),
                    "is_atc": True  # Only showing ATC msgs for now or we could parse pilot ones
                })
            self.sim_data.write_comms_for_overlay(overlay_msgs, self.sapi.is_connected)
        except Exception as e:
            logger.debug(f"Failed to update overlay: {e}")
        
        # Update ComLink with comms
        if self.comlink:
            comms_dicts = []
            for entry in entries:
                comms_dicts.append({
                    "station_name": entry.station_name,
                    "frequency": entry.frequency,
                    "incoming_message": entry.incoming_message,
                    "outgoing_message": entry.outgoing_message,
                    "atc_url": entry.atc_url
                })
            self._cached_comms = comms_dicts
            self.comlink.update_comms(comms_dicts)
        
        # Process messages through copilot (for auto-tune, auto-squawk)
        for entry in entries:
            if entry.outgoing_message:  # ATC messages
                comm_id = hash(entry.outgoing_message + str(entry.timestamp))
                if comm_id not in self._played_comm_ids:
                    # Let copilot parse the message
                    actions = self.copilot.process_atc_message(
                        entry.outgoing_message, 
                        entry.station_name
                    )
                    if actions:
                        logger.info(f"Copilot actions: {actions}")
            
        # Auto-play new audio (runs in background to avoid blocking)
        for entry in entries:
            if entry.atc_url:
                comm_id = hash(entry.atc_url)
                
                # If this is the initial load, just mark as played without playing
                # unless it's very recent (e.g. last 10 seconds)? For now, ignore all old history audio.
                if not self._initial_load_complete:
                    self._played_comm_ids.add(comm_id)
                    continue
                
                if comm_id not in self._played_comm_ids:
                    self._played_comm_ids.add(comm_id)
                    # Queue in background to avoid any potential blocking
                    self._run_in_background(
                        lambda url=entry.atc_url, station=entry.station_name, 
                               freq=entry.frequency, msg=entry.outgoing_message: 
                            self.audio.queue_atc_audio(url, station, freq, msg)
                    )
        
        # Mark initial load as complete after processing the first batch
        if not self._initial_load_complete:
            self._initial_load_complete = True
    
    # =========================================================================
    # Audio
    # =========================================================================
    
    @Slot(str, str, str, str)
    def _on_play_audio(self, url: str, station: str, freq: str, message: str):
        """Handle audio play request from comms widget - runs in background."""
        self.status_bar.showMessage(f"Loading audio from {station}...")
        
        def do_queue():
            """This runs in background thread."""
            return self.audio.queue_atc_audio(url, station, freq, message)
        
        def on_done(result):
            if result:
                self.status_message.emit(f"Playing audio from {station}")
            else:
                self.status_message.emit("Failed to queue audio")
        
        self._run_in_background(do_queue, on_done)
    
    @Slot()
    def _play_all_audio(self):
        """Play all audio in history."""
        self.status_bar.showMessage("Queuing all audio...")
    
    @Slot()
    def _stop_audio(self):
        """Stop audio playback."""
        if self.audio:
            self.audio.stop()
            self.status_bar.showMessage("Audio stopped")
    
    @Slot(int)
    def _on_volume_changed(self, value: int):
        """Handle volume change."""
        if self.audio:
            self.audio.set_volume(value / 100.0)
    
    def _on_audio_start(self, item):
        """Callback when audio starts playing."""
        self.audio_state_changed.emit("playing", item.station_name)
    
    def _on_audio_complete(self, item):
        """Callback when audio finishes."""
        self.audio_state_changed.emit("idle", "")
    
    def _on_audio_state_change(self, state: PlayerState):
        """Callback for audio state changes."""
        self.audio_state_changed.emit(state.value, "")
    
    @Slot(str, str)
    def _handle_audio_state(self, state: str, info: str):
        """Update UI for audio state changes."""
        self.status_panel.set_audio_state(state, info)
    
    # =========================================================================
    # Transmission
    # =========================================================================
    
    @Slot(str, str)
    def _on_send_transmission(self, message: str, channel: str):
        """Handle pilot transmission - routes through AI for ATC response."""
        if not self.sapi or not self.sapi.is_connected:
            self.status_bar.showMessage("Not connected to ATC")
            return
        
        self.status_bar.showMessage(f"Processing ATC response...")
        
        # Get current telemetry for context
        telemetry = self.sim_data.read_telemetry()
        callsign = telemetry.tail_number if telemetry.connected else "November-One-Two-Three-Alpha-Bravo"
        frequency = telemetry.com1.active if channel == "COM1" else telemetry.com2.active
        
        # NOTE: Logic extracted to build_atc_prompt static method for testability
        
        def do_atc_flow():
            """This runs in background thread: Think -> Speak."""
            # STRATUS-001: Get latency tracker
            latency = get_latency_tracker()
            
            # Build conversation history context (last 10 exchanges)
            if self._atc_history:
                history_context = "\n".join(self._atc_history[-10:])
            else:
                history_context = "(This is the first transmission - no prior context)"
            
            # Use extracted module to build prompt (STRATUS-009)
            atc_prompt = build_atc_prompt(
                telemetry, 
                self.airports, 
                self._update_flight_phase(telemetry), 
                history_context, 
                message,
                overrides=self._identity_overrides
            )

            # STRATUS-001: Mark LLM start
            latency.mark("llm_start")
            
            # Get AI response
            think_result = self.sapi.think(atc_prompt)
            
            # STRATUS-001: Mark LLM complete
            latency.mark("llm_complete")
            
            if not think_result.success:
                latency.abort()
                return think_result
            
            atc_response = str(think_result.data).strip()
            
            # STRATUS-003: Validate LLM response before TTS
            validation = validate_atc_response(atc_response)
            if not validation.valid:
                logger.warning(f"ATC response failed validation: {validation.issues}")
                atc_response = get_fallback_response()
            else:
                atc_response = validation.cleaned_response
            
            # Sanitize for TTS
            atc_response = sanitize_for_tts(atc_response)
            
            # STRATUS-001: Mark TTS start
            latency.mark("tts_start")
            
            # Speak the ATC response
            chan_str = "left" if channel == "COM1" else "right"
            speak_result = self.sapi.say(atc_response, channel=chan_str)
            
            # STRATUS-001: Mark TTS complete
            latency.mark("tts_complete")
            
            # Return both for logging
            return type('ATCResult', (), {
                'success': speak_result.success, 
                'data': atc_response,
                'error': speak_result.error if not speak_result.success else None,
                # STRATUS-004: Include validation info for SECA
                'validation_valid': validation.valid,
                'validation_issues': validation.issues,
                'original_response': validation.original_response,
                'prompt': atc_prompt
            })()
        
        def on_result(response):
            """Handle result on UI thread."""
            # STRATUS-001: End latency measurement
            latency = get_latency_tracker()
            measurement = latency.end()
            
            # STRATUS-004: Log to SECA
            if hasattr(response, 'prompt'):
                seca = get_seca_logger()
                seca.log_response(
                    prompt=response.prompt,
                    response=getattr(response, 'original_response', response.data),
                    validation_valid=getattr(response, 'validation_valid', True),
                    validation_issues=getattr(response, 'validation_issues', []),
                    latency_ms=measurement.total_ms if measurement else None,
                    session_id=measurement.session_id if measurement else ""
                )
            
            if response.success:
                # Save to conversation history for context
                self._atc_history.append(f"PILOT: {message}")
                self._atc_history.append(f"ATC: {response.data}")
                # Limit history to last 20 entries (10 exchanges)
                if len(self._atc_history) > 20:
                    self._atc_history = self._atc_history[-20:]
                
                # Add to visual comms history (for local mode)
                from .comms_widget import CommMessage
                import time
                
                # Add pilot message
                pilot_msg = CommMessage(
                    id=int(time.time() * 1000),
                    station_name=callsign,
                    ident="",
                    frequency=frequency,
                    incoming_message=message,
                    outgoing_message="",
                    has_audio=False
                )
                self.comms_widget.add_message(pilot_msg)
                
                # Add ATC response
                atc_msg = CommMessage(
                    id=int(time.time() * 1000) + 1,
                    station_name="ATC",
                    ident="",
                    frequency=frequency,
                    incoming_message="",
                    outgoing_message=response.data,
                    has_audio=False
                )
                self.comms_widget.add_message(atc_msg)
                
                # Log latency in status
                latency_str = f" ({measurement.total_ms:.0f}ms)" if measurement else ""
                self.status_message.emit(f"ATC: {response.data[:50]}...{latency_str}")
                
                # Phase 22: Co-pilot Action Loop
                # Pass the response to the co-pilot to check for actionable commands
                actions = self.copilot.process_atc_instruction(str(response.data))
                if actions:
                    logger.info(f"Co-pilot executed: {actions}")
                    self.status_message.emit(f"Co-pilot: {', '.join(actions)}")
                
                if self.comlink:
                    self.comlink.send_toast("ATC responded", "success")


            else:
                msg = f"ATC Error: {response.error}"
                self.status_message.emit(msg)
                if self.comlink:
                    self.comlink.send_toast(msg, "error")
        
        def on_error(error):
            # STRATUS-001: Abort latency on error
            latency = get_latency_tracker()
            latency.abort()
            self.status_message.emit(f"Error: {error}")
        
        self._run_in_background(do_atc_flow, on_result, on_error)


    
    def _update_flight_phase(self, telemetry) -> str:
        """
        Update and return the current flight phase based on telemetry.
        
        STRATUS-005: Uses FlightPhaseTracker for robust state machine detection.
        """
        tracker = get_flight_phase_tracker()
        phase = tracker.update(telemetry)
        
        # Return phase description for ATC context
        return tracker.get_atc_context()

    @Slot(str, str)
    def _on_tune_frequency(self, channel: str, freq: str):

        """Handle frequency tune request - runs in background."""
        if not self.sapi or not self.sapi.is_connected:
            return
        
        def do_tune():
            chan = Channel.COM1 if channel == "COM1" else Channel.COM2
            return self.sapi.set_frequency(freq, chan)
        
        def on_result(response):
            if response.success:
                self.status_message.emit(f"Tuned {channel} to {freq}")
            else:
                self.status_message.emit(f"Failed to tune: {response.error}")
        
        self._run_in_background(do_tune, on_result)
    
    @Slot(str)
    def _on_swap_frequency(self, channel: str):
        """Handle frequency swap request - send command to X-Plane."""
        if channel == "COM1":
            self.sim_data.swap_com1()
        else:
            self.sim_data.swap_com2()
        self.status_bar.showMessage(f"Swapped {channel} frequencies")
    
    @Slot()
    def _update_telemetry(self):
        """Poll telemetry from X-Plane and update frequency panel."""
        try:
            telemetry = self.sim_data.read_telemetry()
            
            # Update frequency displays
            if telemetry.com1.power:
                self.frequency_panel.update_com1(
                    telemetry.com1.active, 
                    telemetry.com1.standby
                )
            else:
                self.frequency_panel.update_com1("OFF", "---")
            
            if telemetry.com2.power:
                self.frequency_panel.update_com2(
                    telemetry.com2.active,
                    telemetry.com2.standby
                )
            else:
                self.frequency_panel.update_com2("OFF", "---")
            
            # Update transponder
            self.frequency_panel.update_transponder(
                telemetry.transponder.code,
                telemetry.transponder.mode
            )
            
            # STRATUS-002: Update header frequency display
            com1_freq = telemetry.com1.active if telemetry.com1.power else "OFF"
            com2_freq = telemetry.com2.active if telemetry.com2.power else "OFF"
            self.status_panel.set_frequencies(com1_freq, com2_freq)
            
            # Update ComLink with telemetry
            if self.comlink:
                self.comlink.update_telemetry({
                    "com1": {
                        "active": telemetry.com1.active if telemetry.com1.power else "OFF",
                        "standby": telemetry.com1.standby if telemetry.com1.power else "---",
                        "power": telemetry.com1.power
                    },
                    "com2": {
                        "active": telemetry.com2.active if telemetry.com2.power else "OFF",
                        "standby": telemetry.com2.standby if telemetry.com2.power else "---",
                        "power": telemetry.com2.power
                    },
                    "transponder": {
                        "code": telemetry.transponder.code,
                        "mode": telemetry.transponder.mode
                    }
                })
            
            # --- UPLINK TO ATC CLOUD ---
            now = time.time()
            if self.sapi and self.sapi.is_connected and (not hasattr(self, '_last_sapi_uplink') or now - self._last_sapi_uplink >= 5.0):
                self._last_sapi_uplink = now

                
                uplink_data = {
                    "latitude": telemetry.latitude,
                    "longitude": telemetry.longitude,
                    "altitude_msl": telemetry.altitude_msl,
                    "altitude_agl": telemetry.altitude_agl,
                    "heading_mag": telemetry.heading_mag,
                    "heading_true": telemetry.heading_true,
                    "pitch": telemetry.pitch,
                    "roll": telemetry.roll,
                    "on_ground": telemetry.on_ground,
                    "ias": telemetry.ias,
                    "groundspeed": telemetry.groundspeed,
                    "vertical_speed": telemetry.vertical_speed,
                    "com1_active": telemetry.com1.active,
                    "com1_standby": telemetry.com1.standby,
                    "com2_active": telemetry.com2.active,
                    "com2_standby": telemetry.com2.standby,
                    "transponder_code": telemetry.transponder.code,
                    "transponder_mode": telemetry.transponder.mode,
                    "tail_number": telemetry.tail_number,
                    "icao_type": telemetry.icao_type,
                    "sim": "xplane",
                    "timestamp": now
                }

                
                self._run_in_background(
                    lambda: self.sapi.update_telemetry(uplink_data),
                    lambda response: logger.debug(f"SAPI Telemetry Uplink: {response.success}")
                )
                
                # --- FORCE LOCATION UPDATE ---
                # Some sessions need explicit variable sets to "snap" the brain to a new location
                # We send both space and underscore versions for maximum compatibility
                lat_str = f"{telemetry.latitude:.6f}"
                lon_str = f"{telemetry.longitude:.6f}"
                self._run_in_background(lambda: self.sapi.set_variable("PLANE LATITUDE", lat_str, "A"))
                self._run_in_background(lambda: self.sapi.set_variable("PLANE LONGITUDE", lon_str, "A"))
                self._run_in_background(lambda: self.sapi.set_variable("PLANE_LATITUDE", lat_str, "A"))
                self._run_in_background(lambda: self.sapi.set_variable("PLANE_LONGITUDE", lon_str, "A"))




                # --- EXPLICIT FREQUENCY SYNC ---
                # Some SAPI sessions require explicit frequency setting via setFreq
                if not hasattr(self, '_last_com1_uplink') or self._last_com1_uplink != telemetry.com1.active:
                    self._last_com1_uplink = telemetry.com1.active
                    self._run_in_background(lambda: self.sapi.set_frequency(telemetry.com1.active, Channel.COM1))
                
                if not hasattr(self, '_last_com2_uplink') or self._last_com2_uplink != telemetry.com2.active:
                    self._last_com2_uplink = telemetry.com2.active
                    self._run_in_background(lambda: self.sapi.set_frequency(telemetry.com2.active, Channel.COM2))

            
        except Exception as e:
            logger.debug(f"Telemetry update error: {e}")
    
    # =========================================================================
    # View Options
    # =========================================================================
    
    @Slot()
    def _toggle_always_on_top(self):
        """Toggle always-on-top mode for overlay use."""
        is_on_top = self.always_on_top_action.isChecked()
        
        # We need to hide before changing flags
        self.hide()
        
        current_flags = self.windowFlags()
        
        if is_on_top:
            # maintain existing flags but add Top + Tool (Tool helps on Linux)
            new_flags = current_flags | Qt.WindowStaysOnTopHint | Qt.Tool
        else:
            # Remove Top and Tool, restore standard window
            new_flags = current_flags & ~Qt.WindowStaysOnTopHint & ~Qt.Tool
            new_flags = new_flags | Qt.Window
            
        self.setWindowFlags(new_flags)
        self.show()
        
        # Status update
        state = "Enabled" if is_on_top else "Disabled"
        self.status_bar.showMessage(f"Always on top: {state}")
        logger.info(f"Always on top: {is_on_top}, Flags: {new_flags}")
    
    @Slot()
    def _toggle_compact_mode(self):
        """Toggle compact mode for overlay use over simulator."""
        is_compact = self.compact_action.isChecked()
        
        if is_compact:
            # Hide menu bar and right panel, shrink window
            self.menuBar().hide()
            self.frequency_panel.hide()
            self.setMinimumSize(400, 300)
            self.resize(450, 400)
        else:
            # Restore full UI
            self.menuBar().show()
            self.frequency_panel.show()
            self.setMinimumSize(900, 600)
            self.resize(1200, 800)
        
        self.status_bar.showMessage(f"Compact mode: {'Enabled' if is_compact else 'Disabled'}")
        logger.info(f"Compact mode: {is_compact}")
    
    # =========================================================================
    # Misc
    # =========================================================================
    
    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(self, "About StratusATC",
            "<h2>StratusATC</h2>"
            "<p>Version 1.0.0 (Phase 2)</p>"
            "<p>A native Mac/Linux client for the Stratus.AI ATC service.</p>"
            "<p><a href='https://github.com/user/StratusATC'>GitHub</a></p>"
            "<hr>"
            "<p>This is an open-source community project.</p>"
        )
    
    def closeEvent(self, event: QCloseEvent):
        """Handle window close."""
        # Check if we should minimize to tray instead of closing
        if self._minimize_to_tray and self.tray.is_available:
            event.ignore()
            self.hide()
            self.tray.show_notification(
                "StratusATC",
                "Application minimized to tray. Right-click tray icon to quit."
            )
            return
        
        # Actually closing - clean up
        self._save_settings()  # Save persistent settings
        self._stop_polling()
        
        # Wait for workers to finish
        for worker in self._active_workers:
            worker.quit()
            worker.wait(1000)
        
        if self.audio:
            self.audio.shutdown()
        
        if self.comlink:
            self.comlink.stop()
        
        if self.tray:
            self.tray.hide()
        
        event.accept()
    
    # =========================================================================
    # Settings Handlers
    # =========================================================================
    
    @Slot(str)
    def _on_atc_mode_changed(self, mode: str):
        """Handle ATC mode change from settings panel."""
        logger.info(f"ATC mode changed to: {mode}")
        self.status_bar.showMessage(f"ATC Mode: {mode.capitalize()}")
        
        # TODO: Send mode preference to ATC if supported
        # For now, this is a client-side preference
        
        if self.comlink:
            self.comlink.send_toast(f"ATC Mode: {mode.capitalize()}", "info")
    
    @Slot(bool)
    def _on_cabin_crew_toggled(self, enabled: bool):
        """Handle cabin crew toggle from settings panel."""
        logger.info(f"Cabin crew {'enabled' if enabled else 'disabled'}")
        
        if enabled:
            self.status_bar.showMessage("✈️ Cabin crew enabled - announcements active")
            # TODO: Activate cabin crew entity via SAPI intercom
        else:
            self.status_bar.showMessage("Cabin crew disabled")
        
        if self.comlink:
            state = "enabled" if enabled else "disabled"
            self.comlink.send_toast(f"Cabin crew {state}", "info")
    
    @Slot(bool)
    def _on_tour_guide_toggled(self, enabled: bool):
        """Handle tour guide toggle from settings panel."""
        logger.info(f"Tour guide {'enabled' if enabled else 'disabled'}")
        
        if enabled:
            self.status_bar.showMessage("🗺️ Tour guide enabled - landmark info active")
            # TODO: Activate tour guide entity via SAPI intercom
        else:
            self.status_bar.showMessage("Tour guide disabled")
        
        if self.comlink:
            state = "enabled" if enabled else "disabled"
            self.comlink.send_toast(f"Tour guide {state}", "info")
    
    @Slot(bool)
    def _on_mentor_toggled(self, enabled: bool):
        """Handle mentor toggle from settings panel."""
        logger.info(f"Mentor {'enabled' if enabled else 'disabled'}")
        
        if enabled:
            self.status_bar.showMessage("👨‍✈️ Mentor enabled - ask questions via intercom")
            # TODO: Activate mentor entity via SAPI intercom
        else:
            self.status_bar.showMessage("Mentor disabled")
        
        if self.comlink:
            state = "enabled" if enabled else "disabled"
            self.comlink.send_toast(f"Mentor {state}", "info")


    @Slot()
    def _reset_sapi_session(self):
        """Force a session state refresh to resolve location issues."""
        if not self.sapi or not self.sapi.is_connected:
            self.status_bar.showMessage("Connect to ATC before resetting session")
            return
            
        telemetry = self.sim_data.read_telemetry()
        # Use logic similar to prompt builder for consistency
        override_type = self._identity_overrides.get("type", "")
        icao = override_type if override_type else (telemetry.icao_type if telemetry and telemetry.icao_type else "F70")
        
        self.status_bar.showMessage(f"Resetting session for {icao}...")
        
        def do_reset():
            # If local provider, clear the brain context too
            if hasattr(self.sapi, 'manage_brain'):
                try:
                    self.sapi.manage_brain("clear")
                    logger.info("Cleared local AI brain context")
                except Exception as e:
                    logger.error(f"Failed to clear brain context: {e}")
            
            return self.sapi.reset_session(icao)
            
        def on_result(response):
            if response.success:
                self.comms_widget.clear_history()
                self.status_bar.showMessage(f"Session reset successful for {icao}")
                if self.comlink:
                    self.comlink.send_toast(f"SAPI Session Reset: {icao}", "success")
            else:
                self.status_bar.showMessage(f"Reset failed: {response.error}")
                
        self._run_in_background(do_reset, on_result)

    def _update_brain_status(self):
        """Poll and update local AI brain status if using local provider."""
        if not self.sapi or not hasattr(self.sapi, 'get_brain_status'):
            return

        def do_check():
            return self.sapi.get_brain_status()

        def on_result(status):
            is_running, current_model, available = status
            self.settings_panel.update_brain_status(is_running, current_model, available)
            if self.comlink:
                self.comlink.update_brain_status(is_running, current_model, available)

        self._run_in_background(do_check, on_result)

    @Slot()
    def _on_brain_start_requested(self):
        """Handle request to start local AI brain."""
        if not self.sapi or not hasattr(self.sapi, 'manage_brain'):
            return

        self.status_bar.showMessage("Starting local AI brain (Ollama)...")
        
        def do_start():
            return self.sapi.manage_brain("start")

        def on_result(success):
            if success:
                self.status_bar.showMessage("Brain mission started successfully")
            else:
                self.status_bar.showMessage("Failed to start brain. Check systemd status.")

        self._run_in_background(do_start, on_result)

        self._run_in_background(do_start, on_result)

    @Slot(str)
    def _on_callsign_override_changed(self, text: str):
        """Update callsign override."""
        self._identity_overrides["callsign"] = text.strip()
        logger.info(f"Callsign override: '{text}'")
        
    @Slot(str)
    def _on_type_override_changed(self, text: str):
        """Update aircraft type override."""
        self._identity_overrides["type"] = text.strip()
        logger.info(f"Aircraft Type override: '{text}'")

    @staticmethod
    def build_atc_prompt(telemetry, airports, flight_phase, history_context, message, overrides=None):
        """
        Build the ATC system prompt with dynamic location context.
        Static method for easier testing.
        overrides: dict with 'callsign' and 'type' keys
        """
        if overrides is None:
            overrides = {}
            
        # Determine Callsign: Manual Override > Telemetry Connected > Fallback
        manual_callsign = overrides.get("callsign", "")
        if manual_callsign:
             callsign = manual_callsign
        else:
             callsign = telemetry.tail_number if telemetry.connected else "November-One-Two-Three-Alpha-Bravo"

        # Determine Type (used in location context)
        manual_type = overrides.get("type", "")
        icao_type = manual_type if manual_type else telemetry.icao_type

        frequency = telemetry.com1.active
        
        # Default facility name
        facility_name = "Generic"

        # Build location context
        if telemetry.connected:
            lat = telemetry.latitude
            lon = telemetry.longitude
            alt = int(telemetry.altitude_msl)
            on_ground = telemetry.on_ground
            heading = int(telemetry.heading_mag)
            speed = int(telemetry.ias)
            
            # Determine likely ATC facility type based on flight phase
            if on_ground:
                facility_hint = "Ground Control or Tower"
            elif alt < 3000:
                facility_hint = "Tower or Approach Control"
            elif alt < 18000:
                facility_hint = "Approach/Departure Control or Center"
            else:
                facility_hint = "Air Route Traffic Control Center (Center)"
            
            # Phase 2: Airport awareness
            # Look up nearest airport using providing airports service
            nearest_apt = airports.find_nearest(lat, lon)
            if nearest_apt:
                raw_name = nearest_apt.name.replace(" Airport", "").replace(" Intl", "").replace(" International", "")
                facility_name = raw_name
            else:
                facility_name = "Local"
            
            location_context = f"""
AIRCRAFT SITUATION:
- Aircraft: {callsign} (Type: {icao_type})
- Flight Phase: {flight_phase}
- Position: {lat:.4f}°N, {abs(lon):.4f}°{'W' if lon < 0 else 'E'}
- Nearest Facility: {facility_name} ({nearest_apt.icao if nearest_apt else 'Unknown'})
- Altitude: {alt} feet MSL
- Heading: {heading}°
- Speed: {speed} knots
- On Ground: {'Yes' if on_ground else 'No'}
- Radio Frequency: {frequency} MHz

You are Air Traffic Control at {facility_name}.
Facility type: {facility_hint}
"""
        else:
            location_context = f"""
AIRCRAFT SITUATION: Simulator disconnected - no position data available.
Aircraft: {callsign}
You are a generic Air Traffic Controller.
"""

        # Build location-aware ATC prompt with FAA-accurate phraseology
        # Uses dynamic facility name AND callsign in examples to prevent hallucination
        atc_prompt = f"""{location_context}


FAA ATC TRANSMISSION FORMAT:
Format: "[Aircraft Callsign], [Facility], [Message]"

OFFICIAL FAA VFR PHRASEOLOGY EXAMPLES (using YOUR callsign {callsign}):

1. INITIAL CONTACT (Cold Call):
Pilot: "{facility_name}, {callsign}, VFR request."
ATC: "{callsign}, {facility_name}, go ahead."

2. FLIGHT FOLLOWING REQUEST:
Pilot: "{callsign} is type {icao_type}, 5 miles south of {facility_name}, 4,500, request flight following to Sacramento."
ATC: "{callsign}, squawk 4521, ident."
(NOTE: Assign a unique 4-digit squawk code. Do NOT give altimeter yet.)

3. RADAR CONTACT:
ATC: "{callsign}, radar contact, 5 miles south of {facility_name}. Altimeter 29.92."

4. SERVICE TERMINATION (Cancel Flight Following):
Pilot: "{callsign}, field in sight, cancel flight following."
ATC: "{callsign}, radar service terminated, squawk VFR, frequency change approved."

5. TRAFFIC ADVISORY:
ATC: "{callsign}, traffic 12 o'clock, 3 miles, northbound, altitude indicates 3,500."

6. RADIO CHECK (Only if asked):
Pilot: "Radio check."
ATC: "{callsign}, readability five."

CRITICAL RULES:
1. ALWAYS use the EXACT callsign "{callsign}" - never substitute a different callsign
2. Start with aircraft callsign, then facility suffix (Ground, Tower, Approach, Center)
3. NEVER say "This is" - just the facility suffix directly  
4. Taxi clearances ALWAYS end with "hold short of runway [XX]"
5. Numbers: "niner" for 9, "two seven zero" for 270, "point" for decimal
6. Be extremely brief - real ATC is terse
7. Track the flight: if pilot requests flight following, acknowledge with squawk code and destination


CONVERSATION CONTEXT:
{history_context}

The pilot now transmitted: "{message}"

Respond as ATC. Give ONLY the radio transmission, no explanations."""
        
        return atc_prompt

    @Slot(str)
    def _on_brain_pull_requested(self, model_name: str):
        """Handle request to pull/download a model."""
        if not self.sapi:
            return
            
        def do_pull():
            # ... existing ...
            pass # (logic is inside methods usually, just placeholder context)
    
    @Slot(bool)
    def _toggle_copilot(self, checked: bool):
        """Enable/Disable Co-pilot automation."""
        if self.copilot:
            self.copilot.set_enabled(checked)
            state = "enabled" if checked else "disabled"
            self.status_bar.showMessage(f"AI Co-pilot {state}")

    # =========================================================================
    # Brain Management Signals
    # =========================================================================
        """Handle request to pull/download a model."""
        if not self.sapi or not hasattr(self.sapi, 'manage_brain'):
            return

        self.status_bar.showMessage(f"Downloading model '{model_name}'... This may take a while.")
        
        def do_pull():
            return self.sapi.manage_brain("pull", model_name)

        def on_result(success):
            if success:
                self.status_bar.showMessage(f"Model '{model_name}' downloaded!")
            else:
                self.status_bar.showMessage(f"Failed to pull model '{model_name}'.")

        self._run_in_background(do_pull, on_result)

    # =========================================================================
    # Settings Persistence (Phase 24)
    # =========================================================================
    
    def _load_settings(self):
        """Load settings from QSettings."""
        settings = QSettings("StratusATC", "NativeClient")
        
        # Geometry
        if settings.value("geometry"):
            self.restoreGeometry(settings.value("geometry"))
        if settings.value("windowState"):
            self.restoreState(settings.value("windowState"))
            
        # Preferences
        settings_dict = {
            "atc_mode": settings.value("atcMode", "Standard"),
            "cabin_crew_enabled": settings.value("cabinCrew", False, type=bool),
            "tour_guide_enabled": settings.value("tourGuide", False, type=bool),
            "mentor_enabled": settings.value("mentor", False, type=bool),
            "callsign_override": settings.value("callsignOverride", ""),
            "aircraft_type_override": settings.value("aircraftTypeOverride", "")
        }
        
        # Apply to Settings Panel
        self.settings_panel.set_settings(settings_dict)
        
        # Apply to Identity Overrides immediately
        self._identity_overrides["callsign"] = settings_dict["callsign_override"]
        self._identity_overrides["type"] = settings_dict["aircraft_type_override"]
        
        logger.info("Settings loaded")

    def _save_settings(self):
        """Save settings to QSettings."""
        settings = QSettings("StratusATC", "NativeClient")
        
        # Geometry
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        
        # Preferences
        current = self.settings_panel.get_settings()
        settings.setValue("atcMode", current["atc_mode"])
        settings.setValue("cabinCrew", current["cabin_crew_enabled"])
        settings.setValue("tourGuide", current["tour_guide_enabled"])
        settings.setValue("mentor", current["mentor_enabled"])
        settings.setValue("callsignOverride", current["callsign_override"])
        settings.setValue("aircraftTypeOverride", current["aircraft_type_override"])
        
        logger.info("Settings saved")


def run_gui(enable_web: bool = True, web_port: int = 8080):

    """
    Run the GUI application.
    
    Args:
        enable_web: If True, start the ComLink web server for tablet/phone access
        web_port: Port for the ComLink web server (default: 8080)
    """
    app = QApplication(sys.argv)
    app.setApplicationName("StratusATC")
    app.setApplicationVersion("1.0.0")
    
    window = MainWindow(enable_web=enable_web, web_port=web_port)
    window.show()
    
    # Print ComLink URL if enabled
    if enable_web and window.comlink:
        print(f"\n📻 ComLink available at: http://localhost:{web_port}/comlink")
        print(f"   Access from any device on your network!\n")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_gui()
