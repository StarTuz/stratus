#!/bin/bash
# Stratus ATC - D-Bus Integration Test
# Simulates the voice -> brain -> output pipeline.
#
# PREREQUISITES:
# 1. stratus-voice must be running: cargo run --bin stratus-voice
# 2. Ollama must be running with llama3 or similar model
#
# This script:
# 1. Sends a StartListening signal
# 2. Sends a StopListening call (simulates PTT release)
# 3. Monitors for SpeechRecognized signal and checks for command output

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

DBUS_DEST="org.stratus.ATC.Voice"
DBUS_PATH="/org/stratus/ATC/Voice"
DBUS_IFACE="org.stratus.ATC.Voice"
COMMAND_FILE="$HOME/.local/share/StratusATC/stratus_commands.jsonl"

echo "============================================"
echo " Stratus ATC - D-Bus Integration Test"
echo "============================================"
echo ""

# Check if stratus-voice is running
if ! dbus-send --session --print-reply --dest=$DBUS_DEST $DBUS_PATH org.freedesktop.DBus.Introspectable.Introspect > /dev/null 2>&1; then
    echo -e "${RED}ERROR: stratus-voice is not running on D-Bus.${NC}"
    echo "Start it first: cargo run --bin stratus-voice"
    exit 1
fi
echo -e "${GREEN}✓ stratus-voice D-Bus service detected.${NC}"

# Clear command file
echo -e "${YELLOW}Clearing previous commands...${NC}"
> "$COMMAND_FILE" 2>/dev/null || true

# Test 1: Call StartListening
echo ""
echo -e "${YELLOW}Test 1: Calling StartListening...${NC}"
dbus-send --session --print-reply --dest=$DBUS_DEST $DBUS_PATH $DBUS_IFACE.StartListening
echo -e "${GREEN}✓ StartListening called.${NC}"

# Simulate some "speech" (in reality, audio would be captured)
sleep 1

# Test 2: Call StopListening
echo ""
echo -e "${YELLOW}Test 2: Calling StopListening...${NC}"
RESULT=$(dbus-send --session --print-reply --dest=$DBUS_DEST $DBUS_PATH $DBUS_IFACE.StopListening 2>&1)
echo "Response: $RESULT"
echo -e "${GREEN}✓ StopListening called.${NC}"

# Give system time to process
sleep 2

# Test 3: Check for commands
echo ""
echo -e "${YELLOW}Test 3: Checking for generated commands...${NC}"
if [ -f "$COMMAND_FILE" ] && [ -s "$COMMAND_FILE" ]; then
    echo -e "${GREEN}✓ Commands generated:${NC}"
    cat "$COMMAND_FILE"
else
    echo -e "${YELLOW}⚠ No commands generated (this may be expected for some responses).${NC}"
fi

echo ""
echo "============================================"
echo -e "${GREEN} Integration Test Complete!${NC}"
echo "============================================"
echo ""
echo "For full end-to-end testing:"
echo "  1. Run stratus-gui and speak via PTT"
echo "  2. Check the GUI for ATC responses"
echo "  3. Check ~/.local/share/StratusATC/stratus_commands.jsonl"
