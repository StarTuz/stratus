"""
SayIntentions GUI Styles

Modern dark theme styling for the native Linux client.
"""

COLORS = {
    # Primary palette
    'bg_primary': '#1a1a2e',
    'bg_secondary': '#16213e',
    'bg_tertiary': '#0f3460',
    'bg_card': '#1f2940',
    
    # Accent colors
    'accent_primary': '#e94560',
    'accent_secondary': '#00d4ff',
    'accent_green': '#00d26a',
    'accent_orange': '#ff9f1c',
    'accent_yellow': '#ffcc00',
    
    # Text colors
    'text_primary': '#ffffff',
    'text_secondary': '#b4b4b4',
    'text_muted': '#6c757d',
    
    # Status colors
    'status_connected': '#00d26a',
    'status_disconnected': '#ff6b6b',
    'status_pending': '#ffcc00',
    
    # Border colors
    'border_light': '#2d3748',
    'border_active': '#00d4ff',
}

DARK_THEME = f"""
/* Main Application */
QMainWindow, QWidget {{
    background-color: {COLORS['bg_primary']};
    color: {COLORS['text_primary']};
    font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
    font-size: 13px;
}}

/* Cards and Panels */
QFrame#card {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 10px;
    padding: 12px;
}}

QGroupBox {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px;
    padding-top: 24px;
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    background-color: {COLORS['bg_card']};
    color: {COLORS['accent_secondary']};
}}

/* Buttons */
QPushButton {{
    background-color: {COLORS['bg_tertiary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    min-height: 24px;
}}

QPushButton:hover {{
    background-color: {COLORS['accent_secondary']};
    color: {COLORS['bg_primary']};
    border-color: {COLORS['accent_secondary']};
}}

QPushButton:pressed {{
    background-color: {COLORS['accent_primary']};
    border-color: {COLORS['accent_primary']};
}}

QPushButton:disabled {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_muted']};
    border-color: {COLORS['bg_secondary']};
}}

QPushButton#primaryButton {{
    background-color: {COLORS['accent_primary']};
    border-color: {COLORS['accent_primary']};
    color: white;
}}

QPushButton#primaryButton:hover {{
    background-color: #ff6b8a;
    border-color: #ff6b8a;
}}

QPushButton#successButton {{
    background-color: {COLORS['accent_green']};
    border-color: {COLORS['accent_green']};
    color: {COLORS['bg_primary']};
}}

QPushButton#pttButton {{
    background-color: {COLORS['bg_tertiary']};
    border: 2px solid {COLORS['accent_secondary']};
    border-radius: 30px;
    min-width: 60px;
    min-height: 60px;
    font-size: 11px;
    font-weight: bold;
}}

QPushButton#pttButton:pressed {{
    background-color: {COLORS['accent_primary']};
    border-color: {COLORS['accent_primary']};
}}

/* Text Input */
QLineEdit {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 6px;
    padding: 8px 12px;
    selection-background-color: {COLORS['accent_secondary']};
}}

QLineEdit:focus {{
    border: 2px solid {COLORS['accent_secondary']};
}}

QLineEdit::placeholder {{
    color: {COLORS['text_muted']};
}}

QTextEdit {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 6px;
    padding: 8px;
    selection-background-color: {COLORS['accent_secondary']};
}}

/* Labels */
QLabel {{
    color: {COLORS['text_primary']};
}}

QLabel#headerLabel {{
    font-size: 18px;
    font-weight: bold;
    color: {COLORS['text_primary']};
}}

QLabel#subheaderLabel {{
    font-size: 12px;
    color: {COLORS['text_secondary']};
}}

QLabel#frequencyLabel {{
    font-size: 24px;
    font-weight: bold;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    color: {COLORS['accent_green']};
}}

QLabel#statusConnected {{
    color: {COLORS['status_connected']};
    font-weight: bold;
}}

QLabel#statusDisconnected {{
    color: {COLORS['status_disconnected']};
    font-weight: bold;
}}

/* Sliders */
QSlider::groove:horizontal {{
    background-color: {COLORS['bg_secondary']};
    height: 6px;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background-color: {COLORS['accent_secondary']};
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -5px 0;
}}

QSlider::sub-page:horizontal {{
    background-color: {COLORS['accent_secondary']};
    border-radius: 3px;
}}

/* Scroll Bars */
QScrollBar:vertical {{
    background-color: {COLORS['bg_secondary']};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border_light']};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['accent_secondary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* List Widget */
QListWidget {{
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 6px;
    padding: 4px;
    outline: none;
}}

QListWidget::item {{
    background-color: {COLORS['bg_card']};
    border-radius: 6px;
    padding: 8px;
    margin: 4px;
}}

QListWidget::item:hover {{
    background-color: {COLORS['bg_tertiary']};
}}

QListWidget::item:selected {{
    background-color: {COLORS['bg_tertiary']};
    border: 1px solid {COLORS['accent_secondary']};
}}

/* Status Bar */
QStatusBar {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_secondary']};
    border-top: 1px solid {COLORS['border_light']};
}}

/* Menu Bar */
QMenuBar {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    padding: 4px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS['bg_tertiary']};
    border-radius: 4px;
}}

QMenu {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 6px;
    padding: 4px;
}}

QMenu::item {{
    padding: 6px 24px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {COLORS['accent_secondary']};
    color: {COLORS['bg_primary']};
}}

/* Tooltips */
QToolTip {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 4px;
    padding: 6px;
}}

/* Tab Widget */
QTabWidget::pane {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 6px;
}}

QTabBar::tab {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_secondary']};
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['accent_secondary']};
    border-bottom: 2px solid {COLORS['accent_secondary']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['bg_tertiary']};
}}

/* Progress Bar */
QProgressBar {{
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent_secondary']};
    border-radius: 3px;
}}

/* ComboBox */
QComboBox {{
    background-color: {COLORS['bg_secondary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 6px;
    padding: 6px 12px;
}}

QComboBox:focus {{
    border: 2px solid {COLORS['accent_secondary']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border_light']};
    border-radius: 6px;
    selection-background-color: {COLORS['accent_secondary']};
}}
"""


def get_stylesheet():
    """Get the complete application stylesheet."""
    return DARK_THEME


def get_color(name: str) -> str:
    """Get a specific color by name."""
    return COLORS.get(name, '#ffffff')
