"""
Simulator Plugin Installer

Automatically detects X-Plane installations and installs the SayIntentionsML plugin.
mimicking the behavior of the official Windows client.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Standard X-Plane Paths on Linux
XPLANE_PATHS = [
    Path.home() / "X-Plane 12",
    Path.home() / "X-Plane 11",
    Path.home() / ".local/share/Steam/steamapps/common/X-Plane 12",
    Path.home() / ".local/share/Steam/steamapps/common/X-Plane 11",
    Path.home() / "Desktop/X-Plane 12",
    Path.home() / "Desktop/X-Plane 11",
]

# Source files for the plugin (relative to repository root or installed package)
PLUGIN_FILES = {
    "PI_SayIntentions.py": "adapters/xplane/PI_SayIntentions.py",
    "overlay.py": "adapters/xplane/overlay.py"
}

def find_xplane_path() -> Optional[Path]:
    """Search for X-Plane installation directory."""
    for path in XPLANE_PATHS:
        if path.exists() and (path / "Resources" / "plugins").exists():
            return path
    return None

def install_plugin(xplane_path: Path) -> bool:
    """
    Install the plugin to the given X-Plane directory.
    
    Args:
        xplane_path: Path to X-Plane root folder
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        # Determine paths
        plugins_dir = xplane_path / "Resources" / "plugins"
        python_plugins_dir = plugins_dir / "PythonPlugins"
        target_dir = python_plugins_dir / "SayIntentionsML"
        
        # 1. Ensure PythonPlugins exists (requires XPPython3)
        if not python_plugins_dir.exists():
            # We can't install XPPython3 automatically easily, but we can try creating the folder
            # Usually users installing Python plugins already have it.
            # If not, the plugin just won't load, which is harmless.
            python_plugins_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Created PythonPlugins directory")
            
        # 2. Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 3. Locate source files
        # client/src/core/sim_installer.py -> ... -> SayIntentionsML
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        
        installed_files = []
        
        for filename, rel_path in PLUGIN_FILES.items():
            src_file = repo_root / rel_path
            dst_file = target_dir / filename
            
            if src_file.exists():
                shutil.copy2(src_file, dst_file)
                installed_files.append(filename)
                logger.debug(f"Installed {filename} to {dst_file}")
            else:
                logger.error(f"Source file not found: {src_file}")
                return False
                
        logger.info(f"Successfully installed SayIntentionsML plugin to: {target_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Plugin installation failed: {e}")
        return False

def check_and_install():
    """Run the detection and installation process."""
    logger.info("Checking for simulator installation...")
    
    xp_path = find_xplane_path()
    
    if not xp_path:
        logger.warning("X-Plane installation not found in standard locations.")
        return False
        
    logger.info(f"Found X-Plane at: {xp_path}")
    
    # Optional: Check if already installed and updated?
    # For now, we overwrite to ensure latest version
    
    if install_plugin(xp_path):
        return True
    
    return False
