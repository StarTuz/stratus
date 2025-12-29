# StratusAIml - Linux & Mac Client for Stratus.AI

**Community / Open Source Port**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: Active Development](https://img.shields.io/badge/Status-Active%20Development-brightgreen.svg)]()

A native Linux and macOS client for the [Stratus.AI](https://stratus.ai) ATC service.

> **🎉 BREAKTHROUGH (Dec 23, 2024)**: Native client confirmed feasible!  
> We have successfully tested the REST API and downloaded real ATC audio.  
> See [HANDOFF.md](HANDOFF.md) for full details.

> **Status**: Active Development  
> **Current Focus**: Building the Python client

## What is Stratus.AI?

Stratus.AI provides realistic AI-powered Air Traffic Control for flight simulators. Their official client is Windows-only. This project aims to bring native support to Linux and macOS users.

## Project Structure

```
StratusML/
├── client/                 # Native Python client (GUI + Audio)
│   └── src/
│       ├── core/          # Business logic & SAPI interface
│       ├── ui/            # PySide6 GUI (Qt)
│       ├── audio/         # Audio capture/playback
│
├── adapters/
│   └── xplane/            # X-Plane Plugin (Python)
│       ├── PI_Stratus.py  # Main plugin file
│       └── overlay.py           # In-sim overlay widget
│
└── docs/                   # Documentation
```

## Quick Start

### 1. Prerequisites (X-Plane Users)

You must install **XPPython3** for the adapter plugin to work.
- Download: [https://xppython3.readthedocs.io/en/latest/usage/installation_plugin.html](https://xppython3.readthedocs.io/en/latest/usage/installation_plugin.html)
- Extract the `zip` file into your `X-Plane/Resources/plugins/` folder.

### 2. Setup the Client

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r client/requirements.txt
```

### 3. Run

```bash
# Launch the client (GUI + ComLink web server)
# Automatically installs the X-Plane plugin on first run!
python client/src/main.py
```

### 4. Access ComLink (For Fullscreen/VR Users)

Open in any browser (tablet, phone, second monitor):
```
http://localhost:8080/comlink
```

This touch-friendly web interface lets you interact with ATC without alt-tabbing out of your fullscreen simulator.

### Alternative Modes

```bash
# Headless mode (web + audio only, no GUI window)
python client/src/main.py --web

# GUI without web server
python client/src/main.py --no-web

# CLI mode
python client/src/main.py --cli
```

## Simulator Support

| Simulator | Linux | macOS | Status |
|-----------|-------|-------|--------|
| X-Plane 12 | ✅ | 🔜 | Native plugin |
| X-Plane 11 | ✅ | 🔜 | Native plugin |
| MSFS 2024 | 🔄 | ❌ | Via Proton bridge |
| MSFS 2020 | 🔄 | ❌ | Via Proton bridge |

- ✅ Supported
- 🔜 In Progress
- 🔄 Planned (requires Proton)
- ❌ Not Possible

## Architecture

This project uses **SimAPI**, the same file-based protocol as the official Windows client:

```
┌─────────────┐      JSON Files       ┌──────────────────┐
│  X-Plane    │ ──────────────────────│  Native Client   │
│  Plugin     │  simAPI_input.json    │  (Python/Qt)     │
│  (C)        │ <─────────────────────│                  │
│             │  simAPI_output.jsonl  │                  │
└─────────────┘                       └────────┬─────────┘
                                               │ REST/Audio
                                               ▼
                                      ┌──────────────────┐
                                      │ Stratus.AI │
                                      │ Cloud (SAPI)     │
                                      └──────────────────┘
```

## Documentation

- **[HANDOFF.md](HANDOFF.md)** - 🎉 Project handoff with breakthrough confirmation
- **[SAPI Findings](docs/SAPI_FINDINGS.md)** - API research with live test results
- [Project Status](PROJECT_STATUS.md) - Current state and next steps
- [Assessment and Roadmap](ASSESSMENT_AND_ROADMAP.md) - Technical feasibility study
- [X-Plane 12 Platform State](docs/XPLANE_12_PLATFORM.md) - Current XP12 features & Web API
- [X-Plane Extensions](docs/XPLANE_EXTENSIONS.md) - Integrations to fill X-Plane feature gaps
- [X-Plane Plugin README](adapters/xplane/README.md) - Build instructions

## Contributing

This is an open-source community project. Contributions welcome!

## License

MIT License

## Disclaimer

This is an unofficial community project and is not affiliated with Stratus.AI. 
Use of the Stratus.AI service requires a valid subscription from the official provider.
