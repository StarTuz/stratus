"""
Simulator Plugin Installer

Automatically detects X-Plane installations and installs the StratusATC plugin.
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
    "PI_Stratus.py": "adapters/xplane/PI_Stratus.py",
    "overlay.py": "adapters/xplane/overlay.py"
}

XPPYTHON3_URL = "https://xppython3.readthedocs.io/en/latest/_downloads/xp3-linux.zip"

def find_xplane_path() -> Optional[Path]:
    """Search for X-Plane installation directory."""
    
    # 1. Check strict registry file (best method)
    install_file = Path.home() / ".x-plane" / "x-plane_install_12.txt"
    if install_file.exists():
        try:
            lines = install_file.read_text().splitlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                    
                path = Path(line)
                if path.exists():
                    logger.info(f"Found X-Plane 12 via registry: {path}")
                    return path
                    
        except Exception as e:
            logger.warning(f"Failed to read X-Plane registry: {e}")

    # 2. Check standard paths
    for path in XPLANE_PATHS:
        if path.exists() and (path / "Resources" / "plugins").exists():
            return path
            
    return None

def install_xppython3(plugins_dir: Path) -> bool:
    """Download and install XPPython3 if missing."""
    import zipfile
    import tempfile
    import subprocess
    
    xppython_dir = plugins_dir / "XPPython3"
    if xppython_dir.exists():
        return True # Already installed
        
    logger.info("XPPython3 missing. Downloading via curl...")
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        
        # Use curl to download (bypasses some bot protection)
        cmd = ["curl", "-L", "-o", str(tmp_path), XPPYTHON3_URL]
        subprocess.check_call(cmd)
            
        logger.info("Installing XPPython3...")
        with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
            zip_ref.extractall(plugins_dir)
            
        tmp_path.unlink() # Cleanup
        return True
    except Exception as e:
        logger.error(f"Failed to install XPPython3: {e}")
        return False

def install_plugin(xplane_path: Path) -> bool:
    """
    Install the plugin to the given X-Plane directory.
    """
    try:
        plugins_dir = xplane_path / "Resources" / "plugins"
        python_plugins_dir = plugins_dir / "PythonPlugins"
        target_dir = python_plugins_dir / "StratusATC"
        
        # 1. Ensure XPPython3 is installed
        if not install_xppython3(plugins_dir):
            logger.warning("Could not install XPPython3. Plugin may not load.")
        
        # 2. Ensure PythonPlugins exists
        if not python_plugins_dir.exists():
            python_plugins_dir.mkdir(parents=True, exist_ok=True)
            
        # 3. Target directory IS PythonPlugins (XPPython3 only scans root PI_*.py)
        # We cannot put it in a subdirectory unless we have a loader.
        target_dir = python_plugins_dir
        
        # 4. Locate source files
        # client/src/core/sim_installer.py -> ... -> StratusATC
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        
        for filename, rel_path in PLUGIN_FILES.items():
            src_file = repo_root / rel_path
            dst_file = target_dir / filename
            
            if src_file.exists():
                shutil.copy2(src_file, dst_file)
                logger.debug(f"Installed {filename} to {dst_file}")
            else:
                logger.error(f"Source file not found: {src_file}")
                return False
                
        logger.info(f"Successfully installed StratusATC plugin to: {target_dir}")
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
