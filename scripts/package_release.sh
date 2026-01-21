#!/bin/bash
set -e

# Stratus ATC Release Bundler
# Bundles the GUI, Voice Service, and X-Plane Plugin into a single archive.

VERSION="0.1.0"
DIST_DIR="release/stratus-atv-v$VERSION"
ARCHIVE_NAME="stratus-atc-linux-x64-v$VERSION.tar.gz"

echo "Building Stratus ATC v$VERSION..."

# 1. Clean and Create Dist Directory
rm -rf release
mkdir -p "$DIST_DIR/bin"
mkdir -p "$DIST_DIR/plugin"

# 2. Build Rust Components
echo "Compiling Rust components (Release mode)..."
cd stratus-rs
cargo build --release --bin stratus-gui
cargo build --release --bin stratus-voice
cd ..

cp stratus-rs/target/release/stratus-gui "$DIST_DIR/bin/"
cp stratus-rs/target/release/stratus-voice "$DIST_DIR/bin/"

# 3. Bundle X-Plane Plugin
echo "Bundling X-Plane plugin..."
# Ensure the plugin directory structure exists
cp -r adapters/xplane/StratusATC "$DIST_DIR/plugin/"

# 4. Add Documentation and Scripts
echo "Adding documentation and setup scripts..."
cp README.md "$DIST_DIR/"
cp docs/REALISM_NOTES.md "$DIST_DIR/"

cat << 'EOF' > "$DIST_DIR/install.sh"
#!/bin/bash
echo "Installing Stratus ATC..."
mkdir -p ~/.config/StratusATC
echo "Configuring default config.toml..."
cat << 'EOC' > ~/.config/StratusATC/config.toml
[aircraft]
callsign = "N172SP"
aircraft_type = "C172"

[model]
url = "http://localhost:11434"
name = "llama3"
backend = "BitNet"
EOC

echo "Installation complete. Run ./bin/stratus-gui to start."
EOF
chmod +x "$DIST_DIR/install.sh"

# 5. Create Archive
echo "Creating archive $ARCHIVE_NAME..."
tar -czf "$ARCHIVE_NAME" -C release "stratus-atv-v$VERSION"

echo "Release bundle created successfully at $ARCHIVE_NAME"
