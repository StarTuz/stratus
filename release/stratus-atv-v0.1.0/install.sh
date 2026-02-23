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
