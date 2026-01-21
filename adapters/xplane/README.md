# StratusATC X-Plane Adapter (Native C)

A native C plugin for X-Plane 11/12 that provides bidirectional communication with the StratusATC client.

## Features

- **Telemetry Export**: Exports aircraft position, attitude, radio frequencies, and transponder state
- **Command Input**: Accepts commands to set frequencies and transponder in the simulator
- **High Performance**: Native C++ implementation, updates every frame (or configured Hz)
- **Zero Python**: Replaces the legacy Python/XPPython3 plugin.

## Installation

### Requirements

- X-Plane 11 or 12 (Linux, Mac, Windows)
- **No dependencies**: The plugin is self-contained.

### Manual Installation

1. Build or download the `StratusATC` plugin folder.
2. Copy the plugin folder to specific X-Plane directory:

   ```bash
   cp -r StratusATC "X-Plane/Resources/plugins/"
   ```

3. Restart X-Plane.

## Build Instructions (Linux)

You need `cmake` and `gcc`/`clang`.

```bash
cd adapters/xplane
./setup_sdk.sh  # Download X-Plane SDK headers if missing
mkdir build && cd build
cmake ..
make
```

The compiled plugin will be at `adapters/xplane/StratusATC/lin_x64/StratusATC.xpl`.

## Data Exchange

The plugin communicates with the client via JSON files in `~/.local/share/StratusATC/`:

### Telemetry (Plugin → Client)

File: `stratus_telemetry.json` (Updated at 1Hz or configured rate)

### Commands (Client → Plugin)

File: `stratus_commands.jsonl` (Polled each frame)

## Troubleshooting

### Plugin not loading

- Check `Log.txt` in the X-Plane root directory.
- Verify `StratusATC.xpl` is in `Resources/plugins/StratusATC/lin_x64/`.

### No telemetry data

- Verify the data directory exists: `ls ~/.local/share/StratusATC/`
- Check permissions on `~/.local/share/StratusATC/stratus_telemetry.json`.
