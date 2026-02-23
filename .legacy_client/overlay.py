"""
StratusATC X-Plane In-Sim Overlay

Provides an in-sim widget showing:
- Connection status
- Last 3 ATC communications
- Current frequencies

This is an OPTIONAL add-on to the main plugin.
Requires XPPython3 with ImGui support.
"""

import os
import json
import time
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

try:
    import xp
    from XPPython3 import xp_imgui
    from XPPython3.imgui import imgui
    HAS_IMGUI = True
except ImportError:
    HAS_IMGUI = False
    xp = None


@dataclass
class CommMessage:
    """A communication message to display."""
    station: str
    message: str
    timestamp: float
    is_atc: bool  # True = ATC, False = Pilot


class StratusOverlay:
    """
    In-sim overlay widget for StratusATC.
    
    Shows a small floating panel with recent communications.
    """
    
    def __init__(self):
        self.visible = True
        self.messages: List[CommMessage] = []
        self.max_messages = 3
        
        self.data_dir = Path.home() / ".local" / "share" / "StratusATC"
        self.comms_file = self.data_dir / "comms_display.json"
        
        # Window state
        self.window_x = 50
        self.window_y = 50
        self.window_width = 400
        self.window_height = 200
        
        # Status
        self.connected = False
        self.last_update = 0
        
        if HAS_IMGUI:
            self._setup_imgui()
    
    def _setup_imgui(self):
        """Initialize ImGui window."""
        # Register the window
        xp_imgui.create_window(
            "StratusATC",
            self._draw_callback,
            visible=self.visible
        )
        xp.log("[StratusATC] Overlay initialized")
    
    def _draw_callback(self):
        """ImGui draw callback - renders the overlay content."""
        if not self.visible:
            return
        
        # Check for new comms data
        self._poll_comms()
        
        # Set window style
        imgui.push_style_color(imgui.COLOR_WINDOW_BACKGROUND, (0.1, 0.1, 0.15, 0.9))
        imgui.push_style_color(imgui.COLOR_TITLE_BACKGROUND_ACTIVE, (0.2, 0.4, 0.6, 1.0))
        
        # Begin window
        imgui.set_next_window_size(self.window_width, self.window_height, imgui.COND_FIRST_USE_EVER)
        
        expanded, opened = imgui.begin("StratusATC", True, imgui.WINDOW_NO_COLLAPSE)
        
        if expanded:
            # Status line
            if self.connected:
                imgui.text_colored((0.0, 0.8, 0.4, 1.0), "● Connected")
            else:
                imgui.text_colored((0.8, 0.4, 0.0, 1.0), "○ Disconnected")
            
            imgui.same_line(150)
            imgui.text(f"Messages: {len(self.messages)}")
            
            imgui.separator()
            
            # Communications list
            if not self.messages:
                imgui.text_colored((0.5, 0.5, 0.5, 1.0), "No recent communications")
            else:
                for msg in self.messages[-self.max_messages:]:
                    # Station name with color
                    if msg.is_atc:
                        imgui.text_colored((0.3, 0.7, 1.0, 1.0), f"🗼 {msg.station}")
                    else:
                        imgui.text_colored((1.0, 0.7, 0.3, 1.0), f"✈️ PILOT")
                    
                    # Message text (wrapped)
                    imgui.text_wrapped(msg.message[:100] + ("..." if len(msg.message) > 100 else ""))
                    imgui.spacing()
        
        imgui.end()
        imgui.pop_style_color()
        imgui.pop_style_color()
        
        if not opened:
            self.visible = False
    
    def _poll_comms(self):
        """Check for new communications to display."""
        if not self.comms_file.exists():
            return
        
        try:
            mtime = self.comms_file.stat().st_mtime
            if mtime <= self.last_update:
                return
            
            self.last_update = mtime
            
            with open(self.comms_file, 'r') as f:
                data = json.load(f)
            
            self.connected = data.get("connected", False)
            
            # Parse messages
            self.messages = []
            for msg_data in data.get("messages", []):
                msg = CommMessage(
                    station=msg_data.get("station", "Unknown"),
                    message=msg_data.get("message", ""),
                    timestamp=msg_data.get("timestamp", 0),
                    is_atc=msg_data.get("is_atc", True)
                )
                self.messages.append(msg)
            
        except Exception as e:
            xp.log(f"[StratusATC] Error reading comms: {e}")
    
    def show(self):
        """Show the overlay."""
        self.visible = True
        if HAS_IMGUI:
            xp_imgui.show_window("StratusATC")
    
    def hide(self):
        """Hide the overlay."""
        self.visible = False
        if HAS_IMGUI:
            xp_imgui.hide_window("StratusATC")
    
    def toggle(self):
        """Toggle overlay visibility."""
        if self.visible:
            self.hide()
        else:
            self.show()


# Global overlay instance
_overlay: Optional[StratusOverlay] = None


def init_overlay():
    """Initialize the overlay (call from main plugin XPluginStart)."""
    global _overlay
    if HAS_IMGUI:
        _overlay = StratusOverlay()
        return True
    else:
        # Note: When HAS_IMGUI is False, xp may also be None, so we can't log here
        # Logging should be done by the caller if needed
        return False


def cleanup_overlay():
    """Clean up the overlay (call from main plugin XPluginStop)."""
    global _overlay
    _overlay = None


def toggle_overlay():
    """Toggle overlay visibility."""
    if _overlay:
        _overlay.toggle()
