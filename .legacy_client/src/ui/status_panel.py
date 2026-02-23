"""
Status Panel Widget

Shows connection status, audio status, and volume control.
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QSlider, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot

from .styles import get_color


class StatusPanel(QWidget):
    """Panel showing connection and audio status."""
    
    connect_clicked = Signal()
    disconnect_clicked = Signal()
    volume_changed = Signal(int)  # 0-100
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = False
        self._audio_state = "idle"
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(16)
        
        # Connection status
        conn_layout = QVBoxLayout()
        conn_layout.setSpacing(2)
        
        conn_label = QLabel("ATC Status")
        conn_label.setStyleSheet(f"color: {get_color('text_muted')}; font-size: 10px;")
        conn_layout.addWidget(conn_label)
        
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet(f"color: {get_color('status_disconnected')}; font-size: 16px;")
        status_row.addWidget(self.status_indicator)
        
        self.status_text = QLabel("Disconnected")
        self.status_text.setStyleSheet(f"color: {get_color('text_primary')}; font-weight: bold;")
        status_row.addWidget(self.status_text)
        
        conn_layout.addLayout(status_row)
        layout.addLayout(conn_layout)
        
        # Connect/Disconnect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("successButton")
        self.connect_btn.setFixedWidth(100)
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self.connect_btn)
        
        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet(f"background-color: {get_color('border_light')};")
        layout.addWidget(sep1)
        
        # Audio status
        audio_layout = QVBoxLayout()
        audio_layout.setSpacing(2)
        
        audio_label = QLabel("Audio")
        audio_label.setStyleSheet(f"color: {get_color('text_muted')}; font-size: 10px;")
        audio_layout.addWidget(audio_label)
        
        self.audio_status = QLabel("🔇 Idle")
        self.audio_status.setStyleSheet(f"color: {get_color('text_secondary')};")
        audio_layout.addWidget(self.audio_status)
        
        layout.addLayout(audio_layout)
        
        # Volume control
        vol_layout = QVBoxLayout()
        vol_layout.setSpacing(2)
        
        self.vol_label = QLabel("Volume: 100%")
        self.vol_label.setStyleSheet(f"color: {get_color('text_muted')}; font-size: 10px;")
        vol_layout.addWidget(self.vol_label)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        vol_layout.addWidget(self.volume_slider)
        
        layout.addLayout(vol_layout)
        
        # Mute button
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setFixedSize(32, 32)
        self.mute_btn.setCheckable(True)
        self.mute_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                font-size: 18px;
            }}
            QPushButton:checked {{
                color: {get_color('text_muted')};
            }}
        """)
        self.mute_btn.clicked.connect(self._on_mute_toggled)
        layout.addWidget(self.mute_btn)
        
        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet(f"background-color: {get_color('border_light')};")
        layout.addWidget(sep2)
        
        # STRATUS-002: Frequency display
        freq_layout = QVBoxLayout()
        freq_layout.setSpacing(2)
        
        freq_label = QLabel("Radio")
        freq_label.setStyleSheet(f"color: {get_color('text_muted')}; font-size: 10px;")
        freq_layout.addWidget(freq_label)
        
        freq_row = QHBoxLayout()
        freq_row.setSpacing(12)
        
        self.com1_label = QLabel("COM1: ---")
        self.com1_label.setStyleSheet(f"""
            color: {get_color('text_primary')}; 
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-size: 12px;
            font-weight: bold;
        """)
        freq_row.addWidget(self.com1_label)
        
        self.com2_label = QLabel("COM2: ---")
        self.com2_label.setStyleSheet(f"""
            color: {get_color('text_secondary')}; 
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-size: 12px;
        """)
        freq_row.addWidget(self.com2_label)
        
        freq_layout.addLayout(freq_row)
        layout.addLayout(freq_layout)
        
        layout.addStretch()
        
        # Polling status
        self.polling_label = QLabel("")
        self.polling_label.setStyleSheet(f"color: {get_color('text_muted')}; font-size: 11px;")
        layout.addWidget(self.polling_label)
    
    def _on_connect_clicked(self):
        """Handle connect button click."""
        if self._connected:
            self.disconnect_clicked.emit()
        else:
            self.connect_clicked.emit()
    
    def _on_volume_changed(self, value: int):
        """Handle volume slider change."""
        self.vol_label.setText(f"Volume: {value}%")
        self.volume_changed.emit(value)
        
        # Update mute button icon based on volume
        if value == 0:
            self.mute_btn.setText("🔇")
        elif value < 50:
            self.mute_btn.setText("🔉")
        else:
            self.mute_btn.setText("🔊")
    
    def _on_mute_toggled(self, checked: bool):
        """Handle mute button toggle."""
        if checked:
            self._pre_mute_volume = self.volume_slider.value()
            self.volume_slider.setValue(0)
            self.mute_btn.setText("🔇")
        else:
            self.volume_slider.setValue(getattr(self, '_pre_mute_volume', 100))
    
    def set_connected(self, connected: bool, status_text: str = None):
        """Update connection status display."""
        self._connected = connected
        
        if connected:
            self.status_indicator.setStyleSheet(f"color: {get_color('status_connected')}; font-size: 16px;")
            self.status_text.setText(status_text or "Connected")
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setObjectName("primaryButton")
        else:
            self.status_indicator.setStyleSheet(f"color: {get_color('status_disconnected')}; font-size: 16px;")
            self.status_text.setText(status_text or "Disconnected")
            self.connect_btn.setText("Connect")
            self.connect_btn.setObjectName("successButton")
        
        # Force style update
        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)
    
    def set_audio_state(self, state: str, info: str = ""):
        """Update audio status display."""
        self._audio_state = state
        
        if state == "playing":
            self.audio_status.setText(f"🔊 {info or 'Playing'}")
            self.audio_status.setStyleSheet(f"color: {get_color('accent_green')};")
        elif state == "paused":
            self.audio_status.setText(f"⏸️ Paused")
            self.audio_status.setStyleSheet(f"color: {get_color('accent_yellow')};")
        else:
            self.audio_status.setText("🔇 Idle")
            self.audio_status.setStyleSheet(f"color: {get_color('text_secondary')};")
    
    def set_polling(self, active: bool, interval: float = 0):
        """Update polling status."""
        if active:
            self.polling_label.setText(f"🔄 Polling ({interval}s)")
            self.polling_label.setStyleSheet(f"color: {get_color('accent_green')}; font-size: 11px;")
        else:
            self.polling_label.setText("")
    
    def set_frequencies(self, com1: str = "---", com2: str = "---"):
        """
        Update COM frequency display.
        
        STRATUS-002: Pilots need to see frequency at a glance.
        
        Args:
            com1: COM1 active frequency (e.g., "118.700")
            com2: COM2 active frequency (e.g., "121.500")
        """
        self.com1_label.setText(f"COM1: {com1}")
        self.com2_label.setText(f"COM2: {com2}")
