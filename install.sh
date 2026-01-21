#!/bin/bash
# Stratus ATC - Installation Script
# Builds all components and sets up necessary directories.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

STRATUS_DIR="$HOME/.local/share/StratusATC"
CONFIG_DIR="$HOME/.config/stratus"

echo "============================================"
echo " Stratus ATC - Zero Python Installer"
echo "============================================"
echo ""

# Step 1: Build Rust binaries
echo -e "${YELLOW}[1/5] Building Rust binaries...${NC}"
cd stratus-rs
cargo build --release --bin stratus-voice --bin stratus-gui
cd ..
echo -e "${GREEN}Build complete.${NC}"

# Step 2: Build X-Plane plugin
echo ""
echo -e "${YELLOW}[2/5] Building X-Plane plugin...${NC}"
cd adapters/xplane
if [ ! -d "build" ]; then
    mkdir build
fi
cd build
cmake .. > /dev/null 2>&1 && make > /dev/null 2>&1
if [ -f "StratusATC/lin_x64/StratusATC.xpl" ]; then
    echo -e "${GREEN}X-Plane plugin built successfully.${NC}"
else
    echo -e "${YELLOW}Warning: Plugin build may have failed. Check adapters/xplane/README.md${NC}"
fi
cd ../../..

# Step 3: Create data directory
echo ""
echo -e "${YELLOW}[3/5] Creating data directory at ${STRATUS_DIR}...${NC}"
mkdir -p "$STRATUS_DIR"
echo -e "${GREEN}Done.${NC}"

# Step 4: Create config directory and default config if needed
echo ""
echo -e "${YELLOW}[4/5] Setting up config directory...${NC}"
mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_DIR/voice.toml" ]; then
    cat <<EOF > "$CONFIG_DIR/voice.toml"
# Stratus Voice Configuration
#
# PTT is handled via X-Plane's keybinding system.
# Bind "stratus/ptt" in X-Plane Settings > Keyboard or Joystick.

# Optional: Path to whisper.cpp model (fallback if speechd-ng unavailable)
# whisper_model = "whisper.cpp/models/ggml-tiny.en.bin"

# Optional: Path to whisper.cpp binary
# whisper_bin = "whisper.cpp/main"
EOF
    echo -e "${GREEN}Created $CONFIG_DIR/voice.toml${NC}"
else
    echo -e "${GREEN}Config already exists.${NC}"
fi

# Step 5: Copy binaries to local bin
echo ""
echo -e "${YELLOW}[5/5] Installing binaries to ~/.local/bin/...${NC}"
mkdir -p "$HOME/.local/bin"
cp stratus-rs/target/release/stratus-voice "$HOME/.local/bin/"
cp stratus-rs/target/release/stratus-gui "$HOME/.local/bin/"
echo -e "${GREEN}Done.${NC}"

echo ""
echo "============================================"
echo -e "${GREEN} Installation Complete!${NC}"
echo "============================================"
echo ""
echo "Next Steps:"
echo ""
echo "  1. Install X-Plane plugin:"
echo "     cp -r adapters/xplane/StratusATC \"\$XPLANE_PATH/Resources/plugins/\""
echo ""
echo "  2. Configure PTT in X-Plane:"
echo "     - Go to Settings > Keyboard"
echo "     - Search for 'stratus'"
echo "     - Bind 'Stratus ATC Push-to-Talk' to any key or joystick button"
echo ""
echo "  3. Run the services:"
echo "     stratus-voice  # Voice service"
echo "     stratus-gui    # GUI application"
echo ""
