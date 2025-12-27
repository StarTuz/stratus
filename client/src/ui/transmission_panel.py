"""
Transmission Input Widget

Provides text input and PTT button for pilot transmissions.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QKeySequence, QShortcut

from .styles import get_color


class TransmissionPanel(QWidget):
    """Panel for sending pilot transmissions."""
    
    # Emitted when user sends a transmission
    send_transmission = Signal(str, str)  # message, channel
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_channel = "COM1"
        self._setup_ui()
        self._setup_shortcuts()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header with channel selector
        header_layout = QHBoxLayout()
        
        header = QLabel("✈️ Transmit")
        header.setObjectName("headerLabel")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Channel toggle
        self.channel_btn = QPushButton("COM1")
        self.channel_btn.setFixedWidth(70)
        self.channel_btn.setCheckable(True)
        self.channel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {get_color('accent_green')};
                color: {get_color('bg_primary')};
                font-weight: bold;
                border-radius: 4px;
            }}
            QPushButton:checked {{
                background-color: {get_color('accent_orange')};
            }}
        """)
        self.channel_btn.clicked.connect(self._toggle_channel)
        header_layout.addWidget(self.channel_btn)
        
        layout.addLayout(header_layout)
        
        # Main input area
        input_frame = QFrame()
        input_frame.setObjectName("card")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(10)
        
        # Text input
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Type your transmission... (Enter to send)")
        self.text_input.setMinimumHeight(40)
        self.text_input.setStyleSheet(f"""
            QLineEdit {{
                font-size: 14px;
                padding: 8px 12px;
            }}
        """)
        self.text_input.returnPressed.connect(self._send_text)
        input_layout.addWidget(self.text_input)
        
        # PTT Button
        self.ptt_btn = QPushButton("PTT")
        self.ptt_btn.setObjectName("pttButton")
        self.ptt_btn.setToolTip("Push to Talk (hold SPACE)")
        self.ptt_btn.pressed.connect(self._on_ptt_pressed)
        self.ptt_btn.released.connect(self._on_ptt_released)
        input_layout.addWidget(self.ptt_btn)
        
        layout.addWidget(input_frame)
        
        # Quick phrases
        phrases_layout = QHBoxLayout()
        phrases_layout.setSpacing(6)
        
        quick_phrases = [
            ("Ready to Copy", "Ready to copy"),
            ("Wilco", "Wilco"),
            ("Unable", "Unable"),
            ("Say Again", "Say again"),
            ("Standby", "Standby"),
        ]
        
        for label, phrase in quick_phrases:
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 11px;
                    padding: 4px 8px;
                    background-color: {get_color('bg_secondary')};
                }}
                QPushButton:hover {{
                    background-color: {get_color('bg_tertiary')};
                }}
            """)
            btn.clicked.connect(lambda checked, p=phrase: self._send_quick_phrase(p))
            phrases_layout.addWidget(btn)
        
        phrases_layout.addStretch()
        layout.addLayout(phrases_layout)
    
    def _setup_shortcuts(self):
        """Set up keyboard shortcuts."""
        # Space for PTT (TODO: implement hold detection)
        pass
    
    def _toggle_channel(self):
        """Toggle between COM1 and COM2."""
        if self._current_channel == "COM1":
            self._current_channel = "COM2"
            self.channel_btn.setText("COM2")
            self.channel_btn.setChecked(True)
        else:
            self._current_channel = "COM1"
            self.channel_btn.setText("COM1")
            self.channel_btn.setChecked(False)
    
    def _send_text(self):
        """Send the text input as a transmission."""
        text = self.text_input.text().strip()
        if text:
            self.send_transmission.emit(text, self._current_channel)
            self.text_input.clear()
    
    def _send_quick_phrase(self, phrase: str):
        """Send a quick phrase."""
        self.send_transmission.emit(phrase, self._current_channel)
    
    def _on_ptt_pressed(self):
        """Handle PTT button press (start recording placeholder)."""
        self.ptt_btn.setText("🔴 TX")
        self.ptt_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {get_color('accent_primary')};
                border: 2px solid {get_color('accent_primary')};
                border-radius: 30px;
                min-width: 60px;
                min-height: 60px;
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        # TODO: Start audio capture for voice input
    
    def _on_ptt_released(self):
        """Handle PTT button release."""
        self.ptt_btn.setText("PTT")
        self.ptt_btn.setStyleSheet("")  # Reset to default
        self.ptt_btn.setObjectName("pttButton")
        # TODO: Stop audio capture, send to STT
    
    def set_enabled(self, enabled: bool):
        """Enable/disable transmission controls."""
        self.text_input.setEnabled(enabled)
        self.ptt_btn.setEnabled(enabled)
        
        if not enabled:
            self.text_input.setPlaceholderText("Connect to SAPI to transmit...")
        else:
            self.text_input.setPlaceholderText("Type your transmission... (Enter to send)")
