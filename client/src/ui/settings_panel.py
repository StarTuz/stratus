"""
Settings Panel Widget

Provides configuration for ATC mode, cabin crew, tour guide, and other options.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QGroupBox, QFrame, QPushButton
)
from PySide6.QtCore import Qt, Signal

from .styles import get_color


class SettingsPanel(QWidget):
    """Panel for application settings."""
    
    # Signals for settings changes
    atc_mode_changed = Signal(str)  # "student", "standard", "pro"
    cabin_crew_toggled = Signal(bool)
    tour_guide_toggled = Signal(bool)
    mentor_toggled = Signal(bool)
    session_reset_requested = Signal()
    settings_changed = Signal()  # Generic signal for any setting change

    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("⚙️ Settings")
        title.setObjectName("headerLabel")
        layout.addWidget(title)
        
        # ATC Experience Mode
        atc_group = QGroupBox("ATC Experience")
        atc_layout = QVBoxLayout(atc_group)
        
        mode_row = QHBoxLayout()
        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet(f"color: {get_color('text_secondary')};")
        mode_row.addWidget(mode_label)
        
        self.atc_mode_combo = QComboBox()
        self.atc_mode_combo.addItems(["Student", "Standard", "Pro"])
        self.atc_mode_combo.setCurrentText("Standard")
        self.atc_mode_combo.setToolTip(
            "Student: Slower, explicit ATC with full guidance\n"
            "Standard: True-to-life ATC experience\n"
            "Pro: Advanced - no UI aids, realistic"
        )
        self.atc_mode_combo.currentTextChanged.connect(self._on_atc_mode_changed)
        mode_row.addWidget(self.atc_mode_combo)
        mode_row.addStretch()
        
        atc_layout.addLayout(mode_row)
        
        # Mode description
        self.mode_description = QLabel(self._get_mode_description("Standard"))
        self.mode_description.setWordWrap(True)
        self.mode_description.setStyleSheet(f"""
            color: {get_color('text_muted')};
            font-size: 11px;
            padding: 8px;
            background-color: {get_color('bg_secondary')};
            border-radius: 4px;
        """)
        atc_layout.addWidget(self.mode_description)
        
        layout.addWidget(atc_group)
        
        # AI Crew Options
        crew_group = QGroupBox("AI Crew")
        crew_layout = QVBoxLayout(crew_group)
        
        # Cabin Crew toggle
        self.cabin_crew_check = QCheckBox("Enable Cabin Crew")
        self.cabin_crew_check.setToolTip(
            "AI cabin crew provides announcements for:\n"
            "• Pre-departure safety briefing\n"
            "• Cruise altitude updates\n"
            "• Descent and landing preparation\n"
            "• Arrival announcements"
        )
        self.cabin_crew_check.toggled.connect(self._on_cabin_crew_toggled)
        crew_layout.addWidget(self.cabin_crew_check)
        
        # Tour Guide toggle
        self.tour_guide_check = QCheckBox("Enable Tour Guide (VFR)")
        self.tour_guide_check.setToolTip(
            "AI tour guide provides:\n"
            "• Landmark identification\n"
            "• Points of interest along route\n"
            "• Geographic and historical information\n"
            "Great for VFR sightseeing flights!"
        )
        self.tour_guide_check.toggled.connect(self._on_tour_guide_toggled)
        crew_layout.addWidget(self.tour_guide_check)
        
        # Mentor toggle
        self.mentor_check = QCheckBox("Enable Mentor (Flight Instructor)")
        self.mentor_check.setToolTip(
            "AI flight instructor answers your questions:\n"
            "• 'How do I level off the plane?'\n"
            "• 'What's the proper way to lean the mixture?'\n"
            "• 'When should I lower the flaps?'\n"
            "Ask via INTERCOM channel!"
        )
        self.mentor_check.toggled.connect(self._on_mentor_toggled)
        crew_layout.addWidget(self.mentor_check)
        
        layout.addWidget(crew_group)
        
        # Copilot Options (reference to main copilot toggle)
        copilot_group = QGroupBox("Copilot")
        copilot_layout = QVBoxLayout(copilot_group)
        
        copilot_info = QLabel(
            "The AI Copilot handles routine ATC communications:\n"
            "• Auto-tunes frequencies on handoffs\n"
            "• Sets transponder codes automatically\n"
            "• Performs radio readbacks\n\n"
            "Toggle via the 🤖 button in the Transmit panel."
        )
        copilot_info.setWordWrap(True)
        copilot_info.setStyleSheet(f"color: {get_color('text_secondary')}; font-size: 12px;")
        copilot_layout.addWidget(copilot_info)
        
        layout.addWidget(copilot_group)
        
        # Session Management
        session_group = QGroupBox("Session Management")
        session_layout = QVBoxLayout(session_group)
        
        self.reset_btn = QPushButton("🔄 Reset SAPI Session")
        self.reset_btn.setToolTip("Force a session state refresh to resolve location issues (e.g. stuck at Truckee)")
        self.reset_btn.clicked.connect(self.session_reset_requested.emit)
        session_layout.addWidget(self.reset_btn)
        
        session_info = QLabel(
            "Use this if ATC seems 'stuck' at your departure airport or doesn't recognize you've moved."
        )
        session_info.setWordWrap(True)
        session_info.setStyleSheet(f"color: {get_color('text_muted')}; font-size: 10px;")
        session_layout.addWidget(session_info)
        
        layout.addWidget(session_group)

        
        layout.addStretch()
    
    def _get_mode_description(self, mode: str) -> str:
        """Get description text for ATC mode."""
        descriptions = {
            "Student": (
                "🎓 Student Mode\n"
                "Perfect for learning! ATC speaks slower with explicit instructions. "
                "Progressive taxi guidance enabled. All UI aids and flight information displayed."
            ),
            "Standard": (
                "✈️ Standard Mode\n"
                "True-to-life ATC experience. Normal communication speed. "
                "ATC history, frequencies, and taxi guidance available."
            ),
            "Pro": (
                "🏆 Pro Mode\n"
                "Advanced realistic ATC. No UI aids - ATC history, frequencies, and "
                "progressive taxi guidance removed. For experienced aviators."
            )
        }
        return descriptions.get(mode, "")
    
    def _on_atc_mode_changed(self, mode: str):
        """Handle ATC mode change."""
        self.mode_description.setText(self._get_mode_description(mode))
        self.atc_mode_changed.emit(mode.lower())
        self.settings_changed.emit()
    
    def _on_cabin_crew_toggled(self, enabled: bool):
        """Handle cabin crew toggle."""
        self.cabin_crew_toggled.emit(enabled)
        self.settings_changed.emit()
    
    def _on_tour_guide_toggled(self, enabled: bool):
        """Handle tour guide toggle."""
        self.tour_guide_toggled.emit(enabled)
        self.settings_changed.emit()
    
    def _on_mentor_toggled(self, enabled: bool):
        """Handle mentor toggle."""
        self.mentor_toggled.emit(enabled)
        self.settings_changed.emit()
    
    def get_settings(self) -> dict:
        """Get all current settings."""
        return {
            "atc_mode": self.atc_mode_combo.currentText().lower(),
            "cabin_crew_enabled": self.cabin_crew_check.isChecked(),
            "tour_guide_enabled": self.tour_guide_check.isChecked(),
            "mentor_enabled": self.mentor_check.isChecked()
        }
    
    def set_settings(self, settings: dict):
        """Apply settings from dict."""
        if "atc_mode" in settings:
            mode = settings["atc_mode"].capitalize()
            self.atc_mode_combo.setCurrentText(mode)
        
        if "cabin_crew_enabled" in settings:
            self.cabin_crew_check.setChecked(settings["cabin_crew_enabled"])
        
        if "tour_guide_enabled" in settings:
            self.tour_guide_check.setChecked(settings["tour_guide_enabled"])
        
        if "mentor_enabled" in settings:
            self.mentor_check.setChecked(settings["mentor_enabled"])
