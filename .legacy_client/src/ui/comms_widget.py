"""
Comms History Widget

Displays the communication history with ATC, including audio playback controls.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QFont
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

from .styles import get_color


@dataclass
class CommMessage:
    """A single communication message."""
    id: int
    station_name: str
    ident: str
    frequency: str
    incoming_message: str  # Pilot
    outgoing_message: str  # ATC
    has_audio: bool
    audio_url: Optional[str] = None
    timestamp: Optional[datetime] = None


class CommBubble(QFrame):
    """A single communication bubble in the history."""
    
    play_audio = Signal(str)  # Emits audio URL
    
    def __init__(self, message: CommMessage, parent=None):
        super().__init__(parent)
        self.message = message
        self.setObjectName("card")
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)
        
        # Header row: Station name + frequency + play button
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        # Station info
        station_label = QLabel(f"📡 {self.message.station_name}")
        station_label.setStyleSheet(f"color: {get_color('accent_secondary')}; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(station_label)
        
        # Frequency badge
        freq_label = QLabel(self.message.frequency)
        freq_label.setStyleSheet(f"""
            background-color: {get_color('bg_tertiary')};
            color: {get_color('accent_green')};
            padding: 2px 8px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-weight: bold;
        """)
        header_layout.addWidget(freq_label)
        
        header_layout.addStretch()
        
        # Audio play button
        if self.message.has_audio:
            self.play_btn = QPushButton("🔊")
            self.play_btn.setFixedSize(32, 32)
            self.play_btn.setToolTip("Play ATC audio")
            self.play_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {get_color('accent_primary')};
                    border-radius: 16px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {get_color('accent_green')};
                }}
            """)
            self.play_btn.clicked.connect(self._on_play_clicked)
            header_layout.addWidget(self.play_btn)
        
        layout.addLayout(header_layout)
        
        # Pilot message (if any)
        if self.message.incoming_message:
            pilot_frame = QFrame()
            pilot_frame.setStyleSheet(f"""
                background-color: {get_color('bg_secondary')};
                border-radius: 8px;
                border-left: 3px solid {get_color('accent_orange')};
            """)
            pilot_layout = QVBoxLayout(pilot_frame)
            pilot_layout.setContentsMargins(10, 8, 10, 8)
            
            pilot_header = QLabel("✈️ PILOT")
            pilot_header.setStyleSheet(f"color: {get_color('accent_orange')}; font-size: 10px; font-weight: bold;")
            pilot_layout.addWidget(pilot_header)
            
            pilot_text = QLabel(self.message.incoming_message)
            pilot_text.setWordWrap(True)
            pilot_text.setStyleSheet(f"color: {get_color('text_primary')}; font-size: 13px;")
            pilot_layout.addWidget(pilot_text)
            
            layout.addWidget(pilot_frame)
        
        # ATC message
        if self.message.outgoing_message:
            atc_frame = QFrame()
            atc_frame.setStyleSheet(f"""
                background-color: {get_color('bg_secondary')};
                border-radius: 8px;
                border-left: 3px solid {get_color('accent_secondary')};
            """)
            atc_layout = QVBoxLayout(atc_frame)
            atc_layout.setContentsMargins(10, 8, 10, 8)
            
            atc_header = QLabel("🗼 ATC")
            atc_header.setStyleSheet(f"color: {get_color('accent_secondary')}; font-size: 10px; font-weight: bold;")
            atc_layout.addWidget(atc_header)
            
            atc_text = QLabel(self.message.outgoing_message)
            atc_text.setWordWrap(True)
            atc_text.setStyleSheet(f"color: {get_color('text_primary')}; font-size: 13px;")
            atc_layout.addWidget(atc_text)
            
            layout.addWidget(atc_frame)
        
        # Timestamp
        if self.message.timestamp:
            time_str = self.message.timestamp.strftime("%H:%M:%S Z")
            time_label = QLabel(time_str)
            time_label.setAlignment(Qt.AlignRight)
            time_label.setStyleSheet(f"color: {get_color('text_muted')}; font-size: 10px;")
            layout.addWidget(time_label)
    
    def _on_play_clicked(self):
        """Handle play button click."""
        if self.message.audio_url:
            self.play_audio.emit(self.message.audio_url)
    
    def set_playing(self, playing: bool):
        """Update visual state when audio is playing."""
        if hasattr(self, 'play_btn'):
            if playing:
                self.play_btn.setText("⏸️")
                self.play_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {get_color('accent_green')};
                        border-radius: 16px;
                        font-size: 14px;
                    }}
                """)
            else:
                self.play_btn.setText("🔊")
                self.play_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {get_color('accent_primary')};
                        border-radius: 16px;
                        font-size: 14px;
                    }}
                    QPushButton:hover {{
                        background-color: {get_color('accent_green')};
                    }}
                """)


class CommsHistoryWidget(QWidget):
    """Widget displaying the full communication history."""
    
    play_audio_requested = Signal(str, str, str, str)  # url, station, freq, message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._messages: List[CommMessage] = []
        self._bubbles: List[CommBubble] = []
        self._cleared_ids: set = set()
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 12, 8)
        
        title = QLabel("📻 Communications")
        title.setObjectName("headerLabel")
        header.addWidget(title)
        
        header.addStretch()
        
        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self.clear_history)
        header.addWidget(clear_btn)
        
        layout.addLayout(header)
        
        # Scroll area for messages
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {get_color('bg_primary')};
                border: none;
            }}
        """)
        
        # Container for messages
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(8, 8, 8, 8)
        self.messages_layout.setSpacing(8)
        self.messages_layout.addStretch()
        
        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area)
        
        # Empty state label
        self.empty_label = QLabel("No communications yet.\nConnect to ATC and start your flight!")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {get_color('text_muted')}; padding: 40px;")
        self.messages_layout.insertWidget(0, self.empty_label)
    
    def add_message(self, message: CommMessage):
        """Add a new message to the history."""
        # Hide empty label
        self.empty_label.hide()
        
        # Create bubble
        bubble = CommBubble(message)
        bubble.play_audio.connect(lambda url: self._on_play_audio(message, url))
        
        self._messages.append(message)
        self._bubbles.append(bubble)
        
        # Insert before the stretch
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)
        
        # Scroll to bottom
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )
    
    def _on_play_audio(self, message: CommMessage, url: str):
        """Handle play audio request."""
        self.play_audio_requested.emit(
            url,
            message.station_name,
            message.frequency,
            message.outgoing_message
        )
    
    def clear_history(self):
        """Clear all messages."""
        # Track cleared IDs so they don't reappear
        for msg in self._messages:
            self._cleared_ids.add(msg.id)
            
        for bubble in self._bubbles:
            bubble.deleteLater()
        
        self._messages.clear()
        self._bubbles.clear()
        self.empty_label.show()
    
    def update_from_entries(self, entries: list):
        """Update from a list of CommEntry objects from SAPI."""
        existing_ids = {m.id for m in self._messages}
        
        for i, entry in enumerate(entries):
            # Use URL hash as ID
            msg_id = hash(entry.atc_url) if entry.atc_url else hash(entry.outgoing_message + str(i))
            
            # Skip if already exists OR resulted in ignored/cleared list
            if msg_id in existing_ids or msg_id in self._cleared_ids:
                continue
            
            msg = CommMessage(
                id=msg_id,
                station_name=entry.station_name or "Unknown",
                ident=entry.ident or "",
                frequency=entry.frequency or "---",
                incoming_message=entry.incoming_message or "",
                outgoing_message=entry.outgoing_message or "",
                has_audio=bool(entry.atc_url),
                audio_url=entry.atc_url,
                timestamp=datetime.now()
            )
            self.add_message(msg)
