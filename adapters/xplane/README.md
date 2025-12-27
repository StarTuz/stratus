# SayIntentionsML X-Plane Adapter

A Python plugin for X-Plane 11/12 that provides bidirectional communication with the SayIntentionsML native client.

## Features

- **Telemetry Export**: Exports aircraft position, attitude, radio frequencies, and transponder state
- **Command Input**: Accepts commands to set frequencies and transponder in the simulator
- **Low Latency**: Updates every 0.5 seconds via FlightLoop callback

## Installation

### Requirements
- X-Plane 11 or 12
- XPPython3 plugin installed

### Steps

1. Install XPPython3 from [https://xppython3.readthedocs.io/](https://xppython3.readthedocs.io/)

2. Copy the plugin to your X-Plane plugins folder:
   ```bash
   mkdir -p ~/X-Plane\ 12/Resources/plugins/PythonPlugins/SayIntentionsML
   cp PI_SayIntentions.py ~/X-Plane\ 12/Resources/plugins/PythonPlugins/SayIntentionsML/
   ```

3. Restart X-Plane

4. Check the X-Plane log for: `[SayIntentionsML] Plugin started`

## Data Exchange

The plugin communicates with the client via JSON files in `~/.local/share/SayIntentionsAI/`:

### Telemetry (Plugin → Client)
File: `simAPI_telemetry.json`

```json
{
  "latitude": 37.8136,
  "longitude": -122.4089,
  "altitude_msl": 5000.0,
  "heading_mag": 270.0,
  "com1": {
    "active": "121.500",
    "standby": "118.000",
    "power": true
  },
  "com2": {
    "active": "127.100",
    "standby": "134.225",
    "power": true
  },
  "transponder": {
    "code": "1200",
    "mode": "ALT"
  },
  "timestamp": 1735324800.0,
  "sim": "xplane12"
}
```

### Commands (Client → Plugin)
File: `simAPI_commands.json`

```json
{
  "commands": [
    {"type": "set_com1_standby", "frequency": "127.100"},
    {"type": "swap_com1"},
    {"type": "set_transponder", "code": "4521"}
  ],
  "timestamp": 1735324800.0
}
```

## Supported Commands

| Command | Parameters | Description |
|---------|------------|-------------|
| `set_com1_active` | `frequency` | Set COM1 active frequency |
| `set_com1_standby` | `frequency` | Set COM1 standby frequency |
| `swap_com1` | - | Swap COM1 active/standby |
| `set_com2_active` | `frequency` | Set COM2 active frequency |
| `set_com2_standby` | `frequency` | Set COM2 standby frequency |
| `swap_com2` | - | Swap COM2 active/standby |
| `set_transponder` | `code` | Set transponder squawk code |
| `set_transponder_mode` | `mode` | Set mode (OFF/STBY/ON/ALT) |

## DataRefs Used

### Radios
- `sim/cockpit2/radios/actuators/com1_frequency_hz_833`
- `sim/cockpit2/radios/actuators/com1_standby_frequency_hz_833`
- `sim/cockpit2/radios/actuators/com2_frequency_hz_833`
- `sim/cockpit2/radios/actuators/com2_standby_frequency_hz_833`
- `sim/cockpit/radios/transponder_code`
- `sim/cockpit/radios/transponder_mode`

### Position
- `sim/flightmodel/position/latitude`
- `sim/flightmodel/position/longitude`
- `sim/flightmodel/position/elevation`
- `sim/flightmodel/position/mag_psi`

## Troubleshooting

### Plugin not loading
- Ensure XPPython3 is installed and enabled
- Check X-Plane log for errors

### No telemetry data
- Verify the data directory exists: `ls ~/.local/share/SayIntentionsAI/`
- Check if telemetry file is being updated: `tail -f ~/.local/share/SayIntentionsAI/simAPI_telemetry.json`

### Commands not working
- Check X-Plane log for `[SayIntentionsML]` messages
- Verify command file format is valid JSON
