"""
SayIntentions Main Window

The primary GUI window for the native Linux client.
Uses background threads for all SAPI network calls to prevent UI freezing.
"""

import sys
import os
import logging
from datetime import datetime
from typing import Optional, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QStatusBar, QLabel, QApplication, QMessageBox,
    QSystemTrayIcon
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QThread
from PySide6.QtGui import QAction, QIcon, QCloseEvent

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .styles import get_stylesheet, get_color
from .comms_widget import CommsHistoryWidget
from .frequency_panel import FrequencyPanel
from .transmission_panel import TransmissionPanel
from .status_panel import StatusPanel
from .workers import SimpleWorker
from .system_tray import SystemTray

from core.sapi_interface import SapiService, CommEntry, Channel
from core.sim_data import SimDataInterface
from audio import AudioHandler, PlayerState

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for SayIntentions client."""
    
    # Signals for thread-safe UI updates
    comms_updated = Signal(list)  # List of CommEntry
    connection_changed = Signal(bool, str)  # connected, status_message
    audio_state_changed = Signal(str, str)  # state, info
    status_message = Signal(str)  # For thread-safe status bar updates
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self.sapi: Optional[SapiService] = None
        self.audio: Optional[AudioHandler] = None
        self._polling = False
        self._poll_timer: Optional[QTimer] = None
        self._played_comm_ids: set = set()
        self._active_workers: List[SimpleWorker] = []  # Keep references to prevent GC
        self._minimize_to_tray = True  # Minimize to tray instead of closing
        
        # Initialize
        self._setup_window()
        self._setup_menu()
        self._setup_ui()
        self._setup_tray()
        self._connect_signals()
        self._init_services()
        
        logger.info("Main window initialized")
    
    def _setup_window(self):
        """Configure the main window."""
        self.setWindowTitle("SayIntentionsML - Native Mac/Linux Client")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)
        
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
        
        # Right panel: Frequencies and info
        right_panel = QWidget()
        right_panel.setFixedWidth(320)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        
        self.frequency_panel = FrequencyPanel()
        right_layout.addWidget(self.frequency_panel)
        
        # Placeholder for additional info
        right_layout.addStretch()
        
        content_layout.addWidget(right_panel)
        
        main_layout.addWidget(content_widget, stretch=1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Connect to SAPI to begin.")
    
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
    
    def _setup_tray(self):
        """Initialize system tray."""
        self.tray = SystemTray(self)
        logger.info(f"System tray available: {self.tray.is_available}")
    
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
        """Initialize SAPI, audio, and sim data services."""
        # Initialize audio handler
        self.audio = AudioHandler()
        self.audio.on_playback_start = self._on_audio_start
        self.audio.on_playback_complete = self._on_audio_complete
        self.audio.on_state_change = self._on_audio_state_change
        
        # Initialize sim data interface for X-Plane communication
        self.sim_data = SimDataInterface()
        
        # Start telemetry polling (every 500ms to update frequencies)
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.timeout.connect(self._update_telemetry)
        self._telemetry_timer.start(500)
        
        # Disable transmission until connected
        self.transmission_panel.set_enabled(False)
    
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
        self.status_bar.showMessage("Connecting to SAPI...")
        self.status_panel.set_connected(False, "Connecting...")
        
        def do_connect():
            """This runs in background thread."""
            sapi = SapiService()
            if sapi.connect():
                return sapi
            return None
        
        def on_connected(sapi):
            """This runs on UI thread via signal."""
            if sapi:
                self.sapi = sapi
                self.connection_changed.emit(True, "Connected")
                self.status_message.emit("Connected to SayIntentions API")
                self._refresh_history()
                self._start_polling()
            else:
                self.connection_changed.emit(False, "Connection failed")
                self.status_message.emit("Failed to connect to SAPI")
                QMessageBox.warning(self, "Connection Failed", 
                    "Could not connect to SayIntentions API.\nCheck your API key in config.ini")
        
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
            response = self.sapi.get_comms_history()
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
            response = self.sapi.get_comms_history()
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
        
        # Auto-play new audio (runs in background to avoid blocking)
        for entry in entries:
            if entry.atc_url:
                comm_id = hash(entry.atc_url)
                if comm_id not in self._played_comm_ids:
                    self._played_comm_ids.add(comm_id)
                    # Queue in background to avoid any potential blocking
                    self._run_in_background(
                        lambda url=entry.atc_url, station=entry.station_name, 
                               freq=entry.frequency, msg=entry.outgoing_message: 
                            self.audio.queue_atc_audio(url, station, freq, msg)
                    )
    
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
        """Handle pilot transmission - runs in background thread."""
        if not self.sapi or not self.sapi.is_connected:
            self.status_bar.showMessage("Not connected to SAPI")
            return
        
        self.status_bar.showMessage(f"Transmitting on {channel}...")
        
        def do_send():
            """This runs in background thread."""
            chan = Channel.COM1 if channel == "COM1" else Channel.COM2
            return self.sapi.say_as(message, chan)
        
        def on_result(response):
            """Handle result on UI thread."""
            if response.success:
                self.status_message.emit("Transmission sent")
                # Refresh to get response after delay
                QTimer.singleShot(2000, self._refresh_history)
            else:
                self.status_message.emit(f"Transmission failed: {response.error}")
        
        def on_error(error):
            self.status_message.emit(f"Error: {error}")
        
        self._run_in_background(do_send, on_result, on_error)
    
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
            
        except Exception as e:
            logger.debug(f"Telemetry update error: {e}")
    
    # =========================================================================
    # View Options
    # =========================================================================
    
    @Slot()
    def _toggle_always_on_top(self):
        """Toggle always-on-top mode for overlay use."""
        is_on_top = self.always_on_top_action.isChecked()
        
        if is_on_top:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        
        # Re-show the window (required after changing window flags)
        self.show()
        
        self.status_bar.showMessage(f"Always on top: {'Enabled' if is_on_top else 'Disabled'}")
        logger.info(f"Always on top: {is_on_top}")
    
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
        QMessageBox.about(self, "About SayIntentionsML",
            "<h2>SayIntentionsML</h2>"
            "<p>Version 1.0.0 (Phase 2)</p>"
            "<p>A native Mac/Linux client for the SayIntentions.AI ATC service.</p>"
            "<p><a href='https://github.com/user/SayIntentionsML'>GitHub</a></p>"
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
                "SayIntentionsML",
                "Application minimized to tray. Right-click tray icon to quit."
            )
            return
        
        # Actually closing - clean up
        self._stop_polling()
        
        # Wait for workers to finish
        for worker in self._active_workers:
            worker.quit()
            worker.wait(1000)
        
        if self.audio:
            self.audio.shutdown()
        
        if self.tray:
            self.tray.hide()
        
        event.accept()


def run_gui():
    """Run the GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("SayIntentionsML")
    app.setApplicationVersion("1.0.0")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_gui()
