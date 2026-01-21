#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}✈️  Stratus ATC Plugin Installer${NC}"

# Default X-Plane paths to check
XP_PATHS=(
    "$HOME/X-Plane 12"
    "$HOME/X-Plane 11"
    "$HOME/.steam/steam/steamapps/common/X-Plane 12"
    "$HOME/.local/share/Steam/steamapps/common/X-Plane 12"
)

# Check ~/.x-plane/x-plane_install_12.txt
if [ -f "$HOME/.x-plane/x-plane_install_12.txt" ]; then
    echo "Found installer config at ~/.x-plane/x-plane_install_12.txt"
    # Read first line
    XP_INSTALL_PATH=$(head -n 1 "$HOME/.x-plane/x-plane_install_12.txt")
    if [ -d "$XP_INSTALL_PATH" ]; then
        XP_PATHS=("$XP_INSTALL_PATH" "${XP_PATHS[@]}")
    fi
fi

TARGET_DIR=""

# check if path provided as argument
if [ ! -z "$1" ]; then
    if [ -d "$1" ] && [ -d "$1/Resources/plugins" ]; then
        TARGET_DIR="$1"
    else
        echo -e "${RED}Error: Provided path is not a valid X-Plane directory.${NC}"
        exit 1
    fi
else
    # Auto-detect
    for path in "${XP_PATHS[@]}"; do
        if [ -d "$path" ]; then
            TARGET_DIR="$path"
            break
        fi
    done
fi

if [ -z "$TARGET_DIR" ]; then
    echo -e "${RED}Could not auto-detect X-Plane installation.${NC}"
    echo "Usage: ./install_plugin.sh /path/to/X-Plane"
    exit 1
fi

PLUGIN_DIR="$TARGET_DIR/Resources/plugins/StratusATC"
SOURCE_XPL="adapters/xplane/StratusATC/lin_x64/StratusATC.xpl"

echo "Found X-Plane at: $TARGET_DIR"

if [ ! -f "$SOURCE_XPL" ]; then
    echo -e "${RED}Error: Compiled plugin not found at $SOURCE_XPL${NC}"
    echo "Please run: cd adapters/xplane/build && cmake .. && make"
    exit 1
fi

echo "Installing StratusATC plugin..."

# Create directory structure
mkdir -p "$PLUGIN_DIR/lin_x64"

# Clean up legacy if present
if [ -d "$PLUGIN_DIR/64" ]; then
    echo "Removing legacy 64/ directory..."
    rm -rf "$PLUGIN_DIR/64"
fi

# Copy plugin
cp "$SOURCE_XPL" "$PLUGIN_DIR/lin_x64/"

echo -e "${GREEN}✅ Plugin installed successfully to:${NC}"
echo "   $PLUGIN_DIR"
