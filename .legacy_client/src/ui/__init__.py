"""
UI Module for StratusATC Client

Provides PySide6-based GUI components.
"""

from .main_window import MainWindow, run_gui
from .comms_widget import CommsHistoryWidget, CommMessage
from .frequency_panel import FrequencyPanel
from .transmission_panel import TransmissionPanel
from .status_panel import StatusPanel
from .settings_panel import SettingsPanel
from .system_tray import SystemTray
from .styles import get_stylesheet, get_color, COLORS

__all__ = [
    'MainWindow',
    'run_gui',
    'CommsHistoryWidget',
    'CommMessage',
    'FrequencyPanel',
    'TransmissionPanel',
    'StatusPanel',
    'SettingsPanel',
    'SystemTray',
    'get_stylesheet',
    'get_color',
    'COLORS',
]
