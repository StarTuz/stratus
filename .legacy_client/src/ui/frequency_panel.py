"""
Frequency Panel Widget

Displays current radio frequencies (COM1, COM2) with tune controls.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QLineEdit
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont

from .styles import get_color


class FrequencyDisplay(QFrame):
    """A single frequency display (COM1 or COM2)."""
    
    frequency_changed = Signal(str, str)  # channel, new_freq
    swap_clicked = Signal(str)  # channel
    
    def __init__(self, channel: str, parent=None):
        super().__init__(parent)
        self.channel = channel
        self._active_freq = "---"
        self._standby_freq = "---"
        self.setObjectName("card")
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        
        # Channel header
        header = QLabel(self.channel)
        header.setStyleSheet(f"""
            color: {get_color('accent_secondary')};
            font-size: 12px;
            font-weight: bold;
        """)
        layout.addWidget(header)
        
        # Active frequency display
        freq_layout = QHBoxLayout()
        
        self.active_label = QLabel(self._active_freq)
        self.active_label.setStyleSheet(f"""
            color: {get_color('accent_green')};
            font-size: 28px;
            font-weight: bold;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
        """)
        freq_layout.addWidget(self.active_label)
        
        # Swap button
        swap_btn = QPushButton("⇄")
        swap_btn.setFixedSize(32, 32)
        swap_btn.setToolTip("Swap active/standby")
        swap_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {get_color('bg_tertiary')};
                border-radius: 16px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {get_color('accent_secondary')};
            }}
        """)
        swap_btn.clicked.connect(self._swap_frequencies)
        freq_layout.addWidget(swap_btn)
        
        layout.addLayout(freq_layout)
        
        # Standby frequency
        standby_layout = QHBoxLayout()
        
        standby_label = QLabel("STBY:")
        standby_label.setStyleSheet(f"color: {get_color('text_muted')}; font-size: 11px;")
        standby_layout.addWidget(standby_label)
        
        self.standby_input = QLineEdit(self._standby_freq)
        self.standby_input.setMaxLength(7)
        self.standby_input.setFixedWidth(80)
        self.standby_input.setStyleSheet(f"""
            QLineEdit {{
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 14px;
                padding: 4px 8px;
            }}
        """)
        self.standby_input.returnPressed.connect(self._on_standby_entered)
        standby_layout.addWidget(self.standby_input)
        
        standby_layout.addStretch()
        layout.addLayout(standby_layout)
    
    def set_active_frequency(self, freq: str):
        """Set the active frequency display."""
        self._active_freq = freq
        self.active_label.setText(freq)
    
    def set_standby_frequency(self, freq: str):
        """Set the standby frequency."""
        self._standby_freq = freq
        self.standby_input.setText(freq)
    
    def _swap_frequencies(self):
        """Emit signal to swap active and standby frequencies."""
        self.swap_clicked.emit(self.channel)
    
    def _on_standby_entered(self):
        """Handle standby frequency input."""
        new_standby = self.standby_input.text()
        self._standby_freq = new_standby
        self.frequency_changed.emit(self.channel, new_standby)


class FrequencyPanel(QWidget):
    """Panel showing COM1 and COM2 frequencies."""
    
    tune_frequency = Signal(str, str)  # channel, frequency
    swap_frequency = Signal(str)  # channel (COM1/COM2)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("📻 Radio Panel")
        header.setObjectName("headerLabel")
        layout.addWidget(header)
        
        # COM1 and COM2 side by side
        radios_layout = QHBoxLayout()
        radios_layout.setSpacing(12)
        
        self.com1 = FrequencyDisplay("COM1")
        self.com1.frequency_changed.connect(self._on_freq_changed)
        self.com1.swap_clicked.connect(self._on_swap_clicked)
        radios_layout.addWidget(self.com1)
        
        self.com2 = FrequencyDisplay("COM2")
        self.com2.frequency_changed.connect(self._on_freq_changed)
        self.com2.swap_clicked.connect(self._on_swap_clicked)
        radios_layout.addWidget(self.com2)
        
        layout.addLayout(radios_layout)
        
        # Transponder (basic display)
        xpdr_frame = QFrame()
        xpdr_frame.setObjectName("card")
        xpdr_layout = QHBoxLayout(xpdr_frame)
        xpdr_layout.setContentsMargins(12, 8, 12, 8)
        
        xpdr_label = QLabel("XPDR:")
        xpdr_label.setStyleSheet(f"color: {get_color('accent_secondary')}; font-size: 12px; font-weight: bold;")
        xpdr_layout.addWidget(xpdr_label)
        
        self.xpdr_display = QLabel("1200")
        self.xpdr_display.setStyleSheet(f"""
            color: {get_color('accent_yellow')};
            font-size: 18px;
            font-weight: bold;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
        """)
        xpdr_layout.addWidget(self.xpdr_display)
        
        xpdr_layout.addStretch()
        
        self.xpdr_mode = QLabel("ALT")
        self.xpdr_mode.setStyleSheet(f"""
            background-color: {get_color('accent_green')};
            color: {get_color('bg_primary')};
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11px;
        """)
        xpdr_layout.addWidget(self.xpdr_mode)
        
        layout.addWidget(xpdr_frame)
    
    def _on_freq_changed(self, channel: str, freq: str):
        """Handle standby frequency change (user typed in standby field)."""
        self.tune_frequency.emit(channel, freq)
    
    def _on_swap_clicked(self, channel: str):
        """Handle swap button click."""
        self.swap_frequency.emit(channel)
    
    def update_com1(self, active: str, standby: str = None):
        """Update COM1 frequencies."""
        self.com1.set_active_frequency(active)
        if standby:
            self.com1.set_standby_frequency(standby)
    
    def update_com2(self, active: str, standby: str = None):
        """Update COM2 frequencies."""
        self.com2.set_active_frequency(active)
        if standby:
            self.com2.set_standby_frequency(standby)
    
    def update_transponder(self, code: str, mode: str = "ALT"):
        """Update transponder display."""
        self.xpdr_display.setText(code)
        self.xpdr_mode.setText(mode)
