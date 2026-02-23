"""
StratusATC Web Interface (ComLink)

Provides a web-based interface accessible from any device on the network.
This is the key feature for fullscreen/VR flight sim users who can't alt-tab.

Access via: http://localhost:8080/comlink
"""

from .server import ComLinkServer, start_comlink_server

__all__ = ["ComLinkServer", "start_comlink_server"]
