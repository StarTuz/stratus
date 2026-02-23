"""
System Tray Integration

Provides system tray icon with minimize-to-tray and notification support.
"""

import logging
from typing import Optional

from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont

logger = logging.getLogger(__name__)


def create_tray_icon_pixmap(size: int = 64, connected: bool = False) -> QPixmap:
    """
    Create a simple tray icon programmatically.
    
    Args:
        size: Icon size in pixels
        connected: If True, show green indicator; if False, show gray
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # Draw main circle (radio wave icon style)
    if connected:
        color = QColor("#00d26a")  # Green
    else:
        color = QColor("#6c757d")  # Gray
    
    painter.setBrush(color)
    painter.setPen(color)
    
    # Draw concentric arcs (radio waves)
    center = size // 2
    painter.drawEllipse(center - 8, center - 8, 16, 16)
    
    # Draw "ML" text
    painter.setPen(QColor("#ffffff"))
    font = QFont("Arial", size // 5, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), 0x84, "ML")  # AlignCenter
    
    painter.end()
    return pixmap


class SystemTray(QObject):
    """
    System tray management for StratusATC.
    
    Provides:
    - Tray icon with status indicator
    - Right-click menu for quick actions
    - Minimize to tray functionality
    - Notifications
    """
    
    # Signals
    show_window = Signal()
    quit_app = Signal()
    toggle_polling = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._connected = False
        self._polling = False
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._menu: Optional[QMenu] = None
        
        self._setup_tray()
    
    def _setup_tray(self):
        """Initialize the system tray icon and menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray not available on this system")
            return
        
        # Create tray icon
        self._tray_icon = QSystemTrayIcon(self.parent())
        self._update_icon()
        
        # Create context menu
        self._menu = QMenu()
        
        # Show/Hide action
        self._show_action = QAction("Show Window", self._menu)
        self._show_action.triggered.connect(self.show_window.emit)
        self._menu.addAction(self._show_action)
        
        self._menu.addSeparator()
        
        # Status display
        self._status_action = QAction("Status: Disconnected", self._menu)
        self._status_action.setEnabled(False)
        self._menu.addAction(self._status_action)
        
        # Toggle polling
        self._polling_action = QAction("Enable Polling", self._menu)
        self._polling_action.setCheckable(True)
        self._polling_action.triggered.connect(self.toggle_polling.emit)
        self._menu.addAction(self._polling_action)
        
        self._menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", self._menu)
        quit_action.triggered.connect(self.quit_app.emit)
        self._menu.addAction(quit_action)
        
        self._tray_icon.setContextMenu(self._menu)
        
        # Double-click to show window
        self._tray_icon.activated.connect(self._on_activated)
        
        # Set tooltip
        self._tray_icon.setToolTip("StratusATC - Disconnected")
        
        # Show the tray icon
        self._tray_icon.show()
        
        logger.info("System tray initialized")
    
    def _update_icon(self):
        """Update the tray icon based on connection status."""
        if self._tray_icon:
            pixmap = create_tray_icon_pixmap(64, self._connected)
            self._tray_icon.setIcon(QIcon(pixmap))
    
    def _on_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window.emit()
    
    def set_connected(self, connected: bool, status_text: str = ""):
        """Update connection status."""
        self._connected = connected
        self._update_icon()
        
        if self._status_action:
            self._status_action.setText(f"Status: {status_text or ('Connected' if connected else 'Disconnected')}")
        
        if self._tray_icon:
            self._tray_icon.setToolTip(f"StratusATC - {status_text or ('Connected' if connected else 'Disconnected')}")
    
    def set_polling(self, polling: bool):
        """Update polling status."""
        self._polling = polling
        if self._polling_action:
            self._polling_action.setChecked(polling)
            self._polling_action.setText("Disable Polling" if polling else "Enable Polling")
    
    def show_notification(self, title: str, message: str, 
                          icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.Information):
        """Show a system notification."""
        if self._tray_icon and QSystemTrayIcon.supportsMessages():
            self._tray_icon.showMessage(title, message, icon, 5000)
    
    def notify_new_comm(self, station: str, message: str):
        """Notify user of new communication."""
        self.show_notification(
            f"📻 {station}",
            message[:100] + "..." if len(message) > 100 else message,
            QSystemTrayIcon.Information
        )
    
    @property
    def is_available(self) -> bool:
        """Check if system tray is available."""
        return self._tray_icon is not None
    
    def hide(self):
        """Hide the tray icon."""
        if self._tray_icon:
            self._tray_icon.hide()
    
    def show(self):
        """Show the tray icon."""
        if self._tray_icon:
            self._tray_icon.show()
